import os, os.path
import re
import tkinter as tk
from functools import wraps
from tkinter import filedialog, ttk
from tkinter.messagebox import showwarning, showinfo, showerror
import yaml
from rag_processor import *
import threading
import queue
from queue import Queue
import subprocess

class DBCollector:
    def __init__(self):
        self.merge_status = None
        self.db_listbox = None
        self.selected_db_folders = None
        self.merge_db_window = None
        self.pdf_btn = None
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
        self.selected_file = None
        self.file_name = 'Unnamed.txt'
        self.chunk_size = 0
        self.markdown_chunks = []

        self.embs_models = {
            "openai": ["text-embedding-3-large", "text-embedding-ada-002"],
            "huggingface": ["intfloat/multilingual-e5-base", "intfloat/multilingual-e5-large", "sergeyzh/LaBSE-ru-turbo"]
        }

        self.transc_models = ["small", "medium", "base", "large_v3"]

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

        # Кнопка Объединить базы
        self.merge_button = tk.Button(btn_frame, text="Объединить базы знаний...", command=self.merge_db)
        self.merge_button.pack(fill="x", pady=10)

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
            defaultextension=".*",  # Укажите расширение по умолчанию
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")],
            initialfile=self.file_name
        )
        if file_path:
            print(f"Файл для сохранения: {file_path}")
            self.root.title("Конструктор БЗ | " + self.file_name)
            return file_path
        else: return None  # Если пользователь отменил выбор

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

    # Проверка директории на наличие файлов/папок
    @staticmethod
    def is_directory_empty(dir_path: str) -> bool:
        try:
            if not os.path.exists(dir_path):
                raise FileNotFoundError(f"Путь {dir_path} не существует")
            if not os.path.isdir(dir_path):
                raise ValueError(f"{dir_path} не является директорией")
            return next(os.scandir(dir_path), None) is None
        except PermissionError:
            print(f"Ошибка: Нет прав доступа к {dir_path}")
            return False

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
        self.output_queue = Queue()
        self.output_queue = self.run_prompt()                          # Запускаю задачу "Применить промпт"
        self.prompt_monitor() # Мониторинг процесса

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
                code, self.result_db = db_maker.db_pre_constructor(self.content, system, user, 60500)
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
        return "Выполнено"

    def prompt_monitor(self):
        try:
            output = self.output_queue.get_nowait()
            if output:
                self.progress.stop()
                self.progress.pack_forget()
                self.apply_button.config(state="normal")
        except queue.Empty:
            pass

        self.root.after(100, self.prompt_monitor)


# ===================================================================================================
# Сбор базы знаний
    # Окно интерфейса сбора базы знаний
    # v
    def view_collect_data_window(self):
        self.collect_data_window = tk.Toplevel(self.root)
        self.collect_data_window.title("Сбор базы знаний")

        """Транскрибация аудиофайла"""

        aud_frame = ttk.Labelframe(self.collect_data_window, text=" Транскрибация аудиофайла ")
        aud_frame.pack(fill="both", padx=5, pady=5)

        ttk.Label(aud_frame, text="Whisper:", width=len("Whisper:")).grid(row=0, column=0, padx=5, pady=5, sticky="nw")

        transc_models_cmb = ttk.Combobox(aud_frame, values=self.transc_models)
        transc_models_cmb.current(0)  # Устанавливаем первый элемент как выбранный
        transc_models_cmb.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        ttk.Label(aud_frame, text="Словарь:\n(Initial prompt)", width=len("(Initial prompt)")).grid(row=1, column=0, padx=5, pady=5)
        self.init_prompt = tk.Text(aud_frame, wrap="word", width=20, height=5)
        self.init_prompt.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        self.start_btn = tk.Button(aud_frame, text="Транскрибировать аудио...", command=self.start_transcription)
        self.start_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        """Парсинг PDF страниц"""

        pdf_frame = ttk.Labelframe(self.collect_data_window, text=" PDF файлы ")
        pdf_frame.pack(fill="both", padx=5, pady=5)

        ttk.Label(pdf_frame, text="Документ:", width=len("Документ:")).grid(row=0, column=0, padx=5, pady=5, sticky="nw")
        self.pdf_btn = tk.Button(pdf_frame, text="Извлечь...", command=self.start_parsing)
        self.pdf_btn.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")


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
            mode='indeterminate'
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

    # PDF парсинг
    def start_parsing(self):
        # Создаем прогресс-бар
        self.pdf_btn.config(state="disabled")
        self.selected_file = filedialog.askopenfilename(title="Открыть файл",
                                                         filetypes=[("Word document", ".docx"),
                                                                    ("PDF document", ".pdf"),
                                                                    ("Excel table", ".xlsx"),
                                                                    ("All Files", ".*")])
        if self.selected_files:
            self.run_parsing()
            self.progress = ttk.Progressbar(self.collect_data_window, mode='indeterminate')
            self.progress.start()
            self.progress.pack(fill="x", pady=5, padx=5)

    @threaded
    def run_parsing(self):
        db_maker = DBConstructor()
        parsed_text = db_maker.document_parser(self.selected_file)
        self.change_text_field(parsed_text)
        self.monitor_parsing()

    def monitor_parsing(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.pdf_btn.config(state="normal")

#===================================================================================================
    # Окно интерфейса векторизации
    # v
    def view_vector_window(self):
        self.db_maker = DBConstructor()

        # Побил на чанки markdown разметкой
        self.markdown_chunks = self.db_maker.split_markdown(self.content)
        print(f"Чанков при первичном разбиении: {len(self.markdown_chunks)}")
        # Готовлю к дроблению markdown чанков
        pc_lens = [len(md.page_content) for md in self.markdown_chunks] # Узнал длины всех чанков, чтобы взять максимум
        max_chunk = max(pc_lens)
        min_chunk = min(pc_lens)

        # Создаем дочернее окно
        self.vector_window = tk.Toplevel(self.root)
        self.vector_window.title("Векторизация")

        def set_model_name(selected_type):
            self.model_name['values'] = self.embs_models[selected_type]
            self.model_name.current(0)  # Устанавливаем первую модель как выбранную

        def update_models(event):
            selected_type = self.model_type.get()
            set_model_name(selected_type)

        model_frame = ttk.LabelFrame(self.vector_window, text="Модель для эмбеддингов")
        model_frame.pack(fill="x", padx=5, pady=5)

        chunk_frame = ttk.LabelFrame(self.vector_window, text="Размер чанка, симв.")
        chunk_frame.pack(fill="x", padx=5, pady=5)

        # Выпадающий список для выбора провайдера моделей
        self.model_type = ttk.Combobox(model_frame, values=list(self.embs_models.keys()))
        self.model_type.pack(fill='x', padx=10, pady=10)

        # Комбобокс для выбора конкретной модели
        self.model_name = ttk.Combobox(model_frame)
        self.model_name.pack(fill='x', padx=10, pady=10)

        self.model_type.current(0)
        set_model_name(self.model_type.get())
        # Привязываем обновление моделей к выбору типа модели
        self.model_type.bind("<<ComboboxSelected>>", update_models)

        # Кнопка Векторизовать
        self.start_vect_button = tk.Button(self.vector_window, text="Векторизовать", command=self.start_vectorization)
        self.start_vect_button.pack(fill="x", padx=10, pady=10)

        def set_value(value):
            if value.isnumeric():
                self.current_size.get()

        self.current_size = tk.IntVar(value=max_chunk)

        # Spinbox для ручного ввода значения
        self.spinbox = ttk.Spinbox(chunk_frame, from_=min_chunk, to=max_chunk,
                                   textvariable=self.current_size, increment=1)
        self.spinbox.pack(anchor="e", padx=10)

        def update_scale(value):
            self.current_size.set(round(float(value)))

        # Scale для изменения значения через ползунок
        self.chunk_scale = ttk.Scale(chunk_frame, orient="horizontal", from_=min_chunk, to=max_chunk,
                                     variable=self.current_size, command=update_scale)
        self.chunk_scale.pack(fill="x", padx=10, pady=10)

        # Привязка изменения переменной к функции
        self.current_size.trace_add("write", lambda *args: set_value(self.spinbox.get()))

        self.vector_window.transient(self.root)
        self.vector_window.grab_set()
    # ^
    # Окно интерфейса векторизации
    # ===================================================================================================

    # Функционал. Реализация векторизации
    # Проверка на Markdown формат
    def check_markdown(self):
        self.content = self.text_area.get("1.0", "end")  # Считал контент
        if re.search(r'^#+\s', self.content, re.MULTILINE):
            self.view_vector_window() # Запустил окно векторизации
        else:
            showwarning("Предупреждение", "Файл не содержит Markdown разметки.")

    # Метод для запуска векторизации в отдельном потоке. Срабатывает по кнопке "Векторизовать" из диалога векторизации
    def start_vectorization(self):
        # Готовлю папку по умолчанию для записи эмбеддингов
        curdir = os.getcwd()
        init_dir = f"{curdir}/FAISS/DB_{self.file_name.split('/')[-1].split('.')[0]}_{self.model_name.get().split('/')[-1]}"
        if not os.path.exists(init_dir): os.makedirs(init_dir)
        self.db_folder = filedialog.askdirectory(initialdir=init_dir, mustexist=False)

        if self.db_folder:
            # Настройка UI
            self.start_vect_button.config(state=tk.DISABLED)
            self.progress = ttk.Progressbar(
                self.vector_window,
                mode='indeterminate'
            )
            self.progress.pack(fill="x", pady=5)
            self.progress.start()

            # Запуск векторизации
            self.output_queue = Queue()
            self.output_queue = self.vectorise()
            self.monitor_vectorization()
        else: os.rmdir(init_dir)

    # Собственно векторизация
    @threaded
    def vectorise(self):
        model_type = self.model_type.get()
        model_index = self.model_type.current()
        model_name = self.model_name.get()
        chunk_size = self.current_size.get()
        langchain_docs = self.db_maker.split_recursive_from_markdown(self.markdown_chunks, chunk_size)

        print(f"Чанков при вторичном разбиении: {len(langchain_docs)}")

        code, result = self.db_maker.vectorizator(langchain_docs, self.db_folder, model_type=model_type, model_name=model_name)

        if code: showinfo(title="Инфо", message=result)
        else: showerror(title="Ошибка", message=result)
        return result

    def monitor_vectorization(self):
        try:
            output = self.output_queue.get_nowait()
            if output:
                self.progress.stop()
                self.progress.pack_forget()
                self.start_vect_button.config(state=tk.NORMAL)
        except queue.Empty:
            pass

        self.vector_window.after(100, self.monitor_vectorization)

# ==============================================================================================================
# Объединение баз знаний
# Окно объединения баз знаний
    def merge_db(self):
        """Окно объединения баз знаний"""
        self.merge_db_window = tk.Toplevel(self.root)
        self.merge_db_window.title("Объединение баз знаний")

        # Фрейм со списком выбранных папок
        list_frame = ttk.Frame(self.merge_db_window)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Листбокс и скроллбар
        self.db_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, width=60, height=8)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.db_listbox.yview)
        self.db_listbox.configure(yscrollcommand=scrollbar.set)

        self.db_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Фрейм с кнопками управления
        btn_frame = ttk.Frame(self.merge_db_window)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        add_btn = ttk.Button(btn_frame, text="+ Добавить", command=self.add_db_folder)
        remove_btn = ttk.Button(btn_frame, text="- Удалить", command=self.remove_db_folder)
        merge_btn = ttk.Button(btn_frame, text="Объединить", command=self.start_merge)
        cancel_btn = ttk.Button(btn_frame, text="Отмена", command=self.merge_cancel)

        add_btn.pack(side=tk.LEFT, padx=2)
        remove_btn.pack(side=tk.LEFT, padx=2)
        merge_btn.pack(side=tk.RIGHT, padx=2)
        cancel_btn.pack(side=tk.RIGHT, padx=2)

        # Статусная строка
        self.merge_status = ttk.Label(self.merge_db_window, text="Выбрано баз: 0")
        self.merge_status.pack(fill=tk.X, padx=5, pady=2)

    def add_db_folder(self):
        """Добавление папки с базой в список"""
        if self.db_folder: initial_dir = "/".join(self.db_folder.split("/")[0:-1])
        else: initial_dir = os.getcwd()
        self.db_folder = filedialog.askdirectory(
            parent=self.merge_db_window,
            title="Выберите папку с базой FAISS",
            initialdir=initial_dir,
            mustexist=True
        )
        if not self.db_folder:
            return
        if self.db_folder and self.validate_db_folder(self.db_folder):
            if self.db_folder not in self.db_listbox.get(0, tk.END):
                self.db_listbox.insert(tk.END, self.db_folder)

                self.update_merge_status()
            else:
                showwarning("Предупреждение", "Эта база уже добавлена!", parent=self.merge_db_window)
        elif self.db_folder:
            showerror("Ошибка", "Выбранная папка не содержит валидную базу FAISS", parent=self.merge_db_window)


    @staticmethod
    def validate_db_folder(path):
        """Проверка структуры папки с базой"""
        required = {'metadata.json', 'index.faiss', 'index.pkl'}
        files = set(os.listdir(path))
        return required.issubset(files)

    def remove_db_folder(self):
        """Удаление выбранной базы из списка"""
        selection = self.db_listbox.curselection()
        if selection:
            self.db_listbox.delete(selection[0])
            self.update_merge_status()

    def update_merge_status(self):
        """Обновление статусной информации"""
        count = self.db_listbox.size()
        self.merge_status.config(text=f"Выбрано баз: {count}")

    def start_merge(self):
        """Запуск процесса объединения баз"""
        self.db_maker = DBConstructor()
        folders = list(self.db_listbox.get(0, tk.END))
        if len(folders) < 2:
            showwarning("Предупреждение", "Выберите минимум 2 базы для объединения", parent=self.merge_db_window)
            return

        result, main_meta = self.db_maker.metadata_loader(folders[-1])
        print(self.db_folder)

        if self.db_folder:
            initial_dir = f"{'/'.join(self.db_folder.split('/')[0:-1])}/DB_Main_{main_meta['embedding_model'].split('/')[-1]}"
        else: initial_dir = os.getcwd()
        print(initial_dir)

        if not os.path.exists(initial_dir): os.makedirs(initial_dir)

        # Выбор папки для сохранения
        output_folder = filedialog.askdirectory(
            parent=self.merge_db_window,
            title="Выберите папку для сохранения объединенной базы",
            initialdir=initial_dir,
            mustexist=False
        )
        if not output_folder:
            os.rmdir(initial_dir)
            return

        if output_folder != initial_dir:
            if self.is_directory_empty(initial_dir):
                os.rename(initial_dir, output_folder)

        # Создаем прогресс-бар
        self.progress = ttk.Progressbar(
            self.merge_db_window,
            mode='indeterminate'
        )
        self.progress.pack(fill=tk.X, padx=5, pady=5)
        self.progress.start()


        # Запускаем в отдельном потоке
        self.output_queue = Queue()
        self.output_queue = self.run_merge_process(folders, output_folder)
        self.monitor_merge_process()

    @threaded
    def run_merge_process(self, folders, output_folder):
        """Запуск объединения в фоновом режиме"""
        try:
            success, message = self.db_maker.merge_databases(folders, output_folder)
            return success, message
        except Exception as e:
            return False, f"Ошибка объединения: {str(e)}"

    def monitor_merge_process(self):
        """Мониторинг выполнения операции"""
        try:
            result = self.output_queue.get_nowait()
            self.progress.stop()
            self.progress.pack_forget()

            if result[0]:
                showinfo("Успешно", result[1], parent=self.merge_db_window)
                self.merge_db_window.destroy()
            else:
                showerror("Ошибка", result[1], parent=self.merge_db_window)

        except queue.Empty:
            self.root.after(100, self.monitor_merge_process)

    def merge_cancel(self):
        self.db_folder = None
        print("Отменяю")
        self.merge_db_window.destroy()

DBCollector()