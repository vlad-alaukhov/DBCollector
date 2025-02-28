import os, os.path
import re
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.messagebox import showwarning, showinfo, showerror
import yaml
import time
from rag_processor import DBConstructor
import threading
import queue
import subprocess

class DBCollector:
    def __init__(self):
        self.output_queue = queue.Queue()
        self.audio_file = None
        self.output_dir = None
        self.output_queue = None
        self.process = None
        self.status_label = None
        self.start_btn = None
        self.data_area = None
        self.collect_data_window = None
        self.worker_thread = None
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

        self.models = {
            "openai": ["text-embedding-3-large", "text-embedding-ada-002"],
            "huggingface": ["intfloat/multilingual-e5-base", "intfloat/multilingual-e5-large"]
        }

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
            return file_path
        return None  # Если пользователь отменил выбор

        # Метод для сохранения файла базы. Используется как кнопка "Сохранить".
        # Если текст появился в чистом окне, то ему присваивается имя Unnamed и вызывается диалог "Сохранить как..."
        #

    def save_file(self):
        self.content = self.text_area.get("1.0", tk.END)

        if self.file_name == "Unnamed.txt" and os.path.exists(self.file_name) == False:
            self.save_as_file()
            print(self.file_name)
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
    def change_text_field(self, text: str | list):
        self.file_name = 'Unnamed.txt'
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert(tk.END, text)
        self.root.title("Конструктор БЗ | " + self.file_name + "*")
        self.file_save_button['state'] = "normal"
        self.file_saveas_button['state'] = "normal"




    def view_collect_data_window(self):
        pass


DBCollector()

