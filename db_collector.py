import os, os.path
import re
import tkinter as tk
from functools import wraps
from tkinter import filedialog, ttk
from tkinter.messagebox import showwarning, showinfo, showerror
import yaml
import time

from PIL.ImageOps import expand
from rag_processor import DBConstructor
import threading
import queue
from queue import Queue
import subprocess

class DBCollector:
    def __init__(self):
        self.status_label = None
        self.init_prompt = None
        self.audio_file = None
        self.output_dir = None
        self.output_queue = None
        self.process = None
        self.start_btn = None
        self.data_area = None
        self.collect_data_window = None
        self.progress = None
        self.spinbox = None
        self.chunk_scale = None
        self.current_size = None
        self.db_maker = None
        self.start_vect_button = None
        self.model_name = None
        self.model_type = None
        self.db_folder = None
        self.vector_window = None
        self.drop_prompts = None
        self.content = None # Содержимое файлов
        self.result_db = None
        self.prompts = {}
        self.selected_files = []
        self.file_name = 'Unnamed.txt'
        self.chunk_size = 0
        self.markdown_chunks = []

        self.embs_models = {
            "openai": ["text-embedding-3-large", "text-embedding-ada-002"],
            "huggingface": ["intfloat/multilingual-e5-base", "intfloat/multilingual-e5-large"]
        }

        self.transc_models = ["small", "base", "large_v3"]

        # Загружаем промпты из файла
        with open('prompts.yaml', 'r', encoding='utf-8') as file: self.prompts = yaml.safe_load(file)

        self.root = tk.Tk()
        self.root.title("Конструктор БЗ | " + self.file_name)

        btn_frame = ttk.Frame(self.root, width=200)
        btn_frame.pack(anchor="e", side='left', fill="both", padx=10)

        # Добавляем элементы в текстовый фрейм
        txt_frame = ttk.Frame(self.root)
        txt_frame.pack(side='right', fill='both', padx=10, pady=10, expand=True)

        self.text_area = tk.Text(txt_frame, wrap='word')
        self.text_area.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(txt_frame, orient="vertical", command=self.text_area.yview)
        scrollbar.pack(side='right', fill='y', pady=10)

        self.text_area["yscrollcommand"] = scrollbar.set

        def on_text_change(event):
            self.file_save_button['state'] = "normal"
            self.file_saveas_button['state'] = "normal"
            self.root.title("Конструктор БЗ | " + self.file_name + "*")

        self.text_area.bind("<KeyRelease>", on_text_change)

        # Кнопка сбора базы знаний
        self.collect_button = ttk.Button(btn_frame, text="Сбор базы знаний...", command=self.view_collect_data_window)
        self.collect_button.pack(fill='x', pady=10)

        # Кнопка для выбора текстовых файлов
        self.file_button = ttk.Button(btn_frame, text="Выбрать файл базы", command=self.select_text_file)
        self.file_button.pack(fill='x', pady=10)

        # Выпадающий список для выбора промпта
        self.drop_prompts = ttk.Combobox(btn_frame, state='disabled')
        self.drop_prompts['values'] = list(self.prompts.keys())
        self.drop_prompts.current(0)  # Устанавливаем первый элемент как выбранный
        self.drop_prompts.pack(fill='x', pady=10)

        # Кнопка Применить промпт
        self.apply_button = ttk.Button(btn_frame, text="Применить промпт", command=self.apply_prompt, state='disabled')
        self.apply_button.pack(fill="x", pady=10)
        # self.apply_button.grid(row=1, column=1, padx=10, pady=10)

        # Кнопка Сохранить
        self.file_save_button = ttk.Button(btn_frame, text="Сохранить", command=self.save_file, state='disabled')
        self.file_save_button.pack(fill="x", pady=10)
        # self.file_save_button.grid(row=2, column=1, padx=10, pady=10)

        # Кнопка Сохранить как
        self.file_saveas_button = ttk.Button(btn_frame, text="Сохранить как...", command=self.save_as_file, state='disabled')
        self.file_saveas_button.pack(fill="x", pady=10)
        # self.file_saveas_button.grid(row=3, column=1, padx=10, pady=10)

        # Кнопка Векторизовать
        self.vect_button = tk.Button(btn_frame, text="Векторизовать...", command=self.check_markdown, state='disabled')
        self.vect_button.pack(fill="x", pady=10)
        # close_button.grid(row=4, column=1, padx=10, pady=10)

        # Кнопка Закрыть
        self.close_button = tk.Button(btn_frame, text="Закрыть", command=self.root.destroy)
        self.close_button.pack(fill="x", pady=10)
        # close_button.grid(row=5, column=1, padx=10, pady=10)

        # Прогресс-бар
        self.progress = ttk.Progressbar(btn_frame, mode='indeterminate')

        self.root.mainloop()
    # ^
    # Главное окно приложения
    #===================================================================================================
    # Диалог открытия файла базы

    def select_text_file(self):
        def check_button_state():
            self.drop_prompts.config(state="normal")
            self.apply_button.config(state="normal")
            self.vect_button.config(state="normal")

        # Выбор одного текстового файла
        self.file_name = filedialog.askopenfilename(title="Открыть файл",
                                                    filetypes=[("Text files", "*.txt"),
                                                               ("Markdown files", "*.md")])

        if self.file_name:
            with open(self.file_name, 'r+') as fn:
                self.content = fn.read()
            if self.content:
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert(tk.END, self.content)
                check_button_state()
                self.root.title("Конструктор БЗ | " + self.file_name)

        # Диалог сохранения файла базы

    def select_save_file(self, overwrite: bool):
        file_path = filedialog.asksaveasfilename(
            parent=self.root,
            confirmoverwrite=overwrite,
            title="Сохранить файл",
            defaultextension=".txt",  # Укажите расширение по умолчанию
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")],
            initialfile=self.file_name
        )
        if file_path:
            print(f"Файл для сохранения: {file_path}")
            self.root.title("Конструктор БЗ | " + self.file_name)
            return file_path
        return None  # Если пользователь отменил выбор

        # Метод для сохранения файла базы. Используется как кнопка "Сохранить".
        # Если текст появился в чистом окне, то ему присваивается имя Unnamed и вызывается диалог "Сохранить как..."
        #

    def save_file(self):
        self.content = self.text_area.get("1.0", tk.END)

        if self.file_name == "Unnamed.txt" and os.path.exists(self.file_name) == False:
            self.save_as_file()
        else:
            with open(self.file_name, 'w') as db_file:
                db_file.write(self.content)
        self.root.title("Конструктор БЗ | " + self.file_name)

        self.file_save_button.config(state="disabled")
        self.file_saveas_button.config(state="disabled")

    # Метод для реализации "Сохранить как..."
    def save_as_file(self):
        self.content = self.text_area.get("1.0", tk.END)
        self.file_name = self.select_save_file(True)
        if self.file_name:
            with open(self.file_name, 'w') as db_file: db_file.write(self.content)
            self.file_save_button.config(state="disabled")
            self.file_saveas_button.config(state="disabled")

    # Обновление текстового поля: имя файла становится Unnamed, текстовое поле очищается,
    # заполняется текстом из аргумента text, заголовок меняется и ставится признае несохраненного файла.
    def clear_text_field(self):
        self.file_name = 'Unnamed.txt'
        self.text_area.delete("1.0", tk.END)
        self.root.title("Конструктор БЗ | " + self.file_name + "*")
        self.file_save_button['state'] = "normal"
        self.file_saveas_button['state'] = "normal"

    def change_text_field(self, text: str | list):
        self.clear_text_field()
        self.text_area.insert(tk.END, text)

    # Проверка на Markdown формат
    def check_markdown(self):
        self.content = self.text_area.get("1.0", "end")  # Считал контент
        if re.search(r'^#+\s', self.content, re.MULTILINE):
            pass # self.view_vector_window()
        else:
            showwarning("Предупреждение", "Файл не содержит Markdown разметки.")

    # ===============================================================================
    # Декоратор для выполнения задачи в потоке
    @staticmethod
    def threaded(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result_queue = Queue()

            def thread_worker():
                try:
                    result = func(*args, **kwargs)
                    result_queue.put(result)
                except Exception as e:
                    result_queue.put(f"ERROR: {str(e)}")

            threading.Thread(target=thread_worker, daemon=True).start()
            return result_queue

        return wrapper

    # Функционал. Реализация команды "Применить промпт"
    def apply_prompt(self):
        self.apply_button.config(state="disabled") # Блокирую кнопки
        self.progress.pack(fill="x")               # Размещаю прогресс-бар
        self.progress.start()                      # Запускаю прогресс-бар
        self.run_prompt()                          # Запускаю задачу "Применить промпт"

    # Задача "Применить промпт работает через декоратор в отдельном потоке
    @threaded
    def run_prompt(self):
        db_maker = DBConstructor() # создаю экземпляр DBConstructor
        # Беру промпт из комбобокса
        selected_prompt_key = self.drop_prompts.get()
        system = self.prompts[selected_prompt_key]['system']
        user = self.prompts[selected_prompt_key]['user']
        # Загружаю контент для базы знаний из текстового поля
        self.content = self.text_area.get("1.0", tk.END)

        code = None

        # Смотрю, какой промпт выбран, и запускаю обработку ChatGPT
        match self.drop_prompts.current():
            case 0:
                print(f"Выбран промпт: {self.drop_prompts.get()}")
                code, self.result_db = db_maker.db_pre_constructor(self.content, system, user, 60500, True)
            case 1 | 2:
                print(f"Выбран промпт: {self.drop_prompts.get()}")
                code, self.result_db = db_maker.db_constructor(self.content, system, user)
            case _:
                showerror("Ошибка", "Этот промпт не для работы с базой знаний")
                self.result_db = self.content

        # Обрабатываю результат и вывожу.
        if code:
            self.change_text_field(self.result_db)
            showinfo("Успешно", f"Выполнен промпт \n\"{self.drop_prompts.get()}\"")
        elif not code:
            self.result_db = self.content
            showerror("Ошибка запроса", self.result_db)
        elif code is None: showerror("Ошибка", "Промпт не выполнен.")
        self.prompt_monitor() # Мониторинг процесса

    def prompt_monitor(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.apply_button.config(state="normal")

# ===================================================================================================
# Сбор базы знаний
    # Окно интерфейса сбора базы знаний
    # v
    def view_collect_data_window(self):
        self.collect_data_window = tk.Toplevel(self.root)
        self.collect_data_window.title("Сбор базы знаний")

        txt_frame = ttk.Labelframe(self.collect_data_window, text=" Транскрибация аудиофайла ")
        txt_frame.pack(fill="both", padx=5, pady=5)

        ttk.Label(txt_frame, text="Whisper:", width=len("Whisper:")).grid(row=0, column=0, padx=5, pady=5, sticky="nw")

        transc_models_cmb = ttk.Combobox(txt_frame, values=self.transc_models)
        transc_models_cmb.current(0)  # Устанавливаем первый элемент как выбранный
        transc_models_cmb.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        ttk.Label(txt_frame, text="Словарь:\n(Initial prompt)", width=len("(Initial prompt)")).grid(row=1, column=0, padx=5, pady=5)
        self.init_prompt = tk.Text(txt_frame, wrap="word", width=20, height=5)
        self.init_prompt.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        self.start_btn = tk.Button(txt_frame, text="Транскрибировать аудио...", command=self.start_transcription)
        self.start_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        self.collect_data_window.transient(self.root)
        self.collect_data_window.grab_set()
    # ^
    # Окно интерфейса сбора базы знаний

    # Транскрибация
    def start_transcription(self):
        self.start_btn.config(state=tk.DISABLED)
        self.audio_file = filedialog.askopenfilename(title="Открыть файл")
        if not self.audio_file:
            self.start_btn.config(state=tk.NORMAL)
            return
        self.output_dir = os.path.dirname(self.audio_file)
        self.clear_text_field()

        # Создаем прогресс-бар
        self.progress = ttk.Progressbar(
            self.collect_data_window,
            mode='indeterminate',
            length=300
        )
        self.progress.pack(fill="x", pady=5, padx=5)
        self.progress.start()

        # Запускаем транскрибацию
        self.output_queue = Queue()
        self.run_whisper_transcription()
        self.monitor_transcription()

    @threaded
    def run_whisper_transcription(self):
        try:
            # Получаем текст из initial prompt
            initial_prompt = self.init_prompt.get("1.0", tk.END).strip()

            cmd = [
                "whisper",
                self.audio_file,
                "--model", "base",
                "--output_dir", self.output_dir,
                "--task", "transcribe",
                "--language", "ru",
                "--verbose", "True",
                "--initial_prompt", initial_prompt,
                "--fp16", "False"
            ]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            # Чтение вывода процесса
            for line in self.process.stdout:
                self.output_queue.put(line)

            # После завершения получаем результат
            self.process.wait()

            if self.process.returncode == 0:
                # Ищем созданный файл
                base_name = os.path.splitext(os.path.basename(self.audio_file))[0]
                output_file = os.path.join(self.output_dir, f"{base_name}.txt")

                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        self.output_queue.put(f.read())
                else:
                    self.output_queue.put("ERROR: Выходной файл не найден")

            self.output_queue.put(None)

        except Exception as e:
            self.output_queue.put(f"ERROR: {str(e)}")
        finally:
            if hasattr(self, 'process') and self.process:
                self.process.stdout.close()

    def monitor_transcription(self):
        try:
            line = self.output_queue.get_nowait()

            if line is None:
                # Завершение операции
                self.on_transcription_done()
                return
            elif line.startswith("ERROR"):
                self.progress.stop()
                self.status_label.config(text=line)
                self.start_btn.config(state=tk.NORMAL)
                return
            # Если получили текст - выводим в поле
            else:
                self.text_area.insert(tk.END, line + "\n")
                self.text_area.see(tk.END)

        except queue.Empty:
            pass

        self.collect_data_window.after(100, self.monitor_transcription)

    def on_transcription_done(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.start_btn.config(state=tk.NORMAL)

        # Проверяем результат
        result = self.text_area.get("1.0", tk.END).strip()
        if result and not result.startswith("ERROR"):
            showinfo("Готово", "Транскрибация успешно завершена")
        else:
            showerror("Ошибка", "Не удалось получить результат транскрибации")

DBCollector()