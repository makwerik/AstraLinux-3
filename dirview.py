import sys
import os
from PyQt5.QtWidgets import (QApplication, QTreeView, QFileSystemModel, QWidget,
                             QVBoxLayout, QLineEdit, QStyledItemDelegate, QPushButton, QHeaderView)

from PyQt5.QtCore import QDir, Qt, QModelIndex


class FileSizeSystemModel(QFileSystemModel):
    """Класс модели файловой системы с дополнительным столбцом для размера папок"""

    def __init__(self):
        # конструктор базового класса QFileSystemModel.
        super().__init__()
        # создаю словарь для кэширования размеров папок, чтобы не пересчитывать их каждый раз
        self.size_cache = {}

    def columnCount(self, parent=QModelIndex()):
        """Переопределяю метод columnCount, чтобы увеличить количество столбцов на 1 для отображения размера папок"""
        return super().columnCount(parent) + 1

    def data(self, index, role=None):
        """Переопределяю метод data, чтобы добавить отображение данных для нового столбца"""
        # проверяю, что работаю с пятой колонкой
        if index.column() == 4:
            # получаю полный путь к файлу или папке.
            file_path = self.filePath(index.sibling(index.row(), 0))
            # проверяю, что необходимо отобразить данные.
            if role == Qt.DisplayRole:
                if os.path.isdir(file_path):
                    return self.size_cache.get(file_path, "")
                else:
                    # для файлов возвращается пустая строка
                    return ""
        # для остальных случаев стандартное поведение базового класса.
        return super().data(index, role)

    def headerData(self, section, orientation, role=None):
        """Переопределяю метод headerData, чтобы задать заголовок для нового столбца"""
        # проверка, что необходимо отобразить заголовок и что ориентация горизонтальная
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            # если это пятая колонка, то устанавливаю заголовок
            if section == 4:
                return "Размер папки"
        return super().headerData(section, orientation,
                                  role)

    def flags(self, index):
        """Переопределяю метод flags, чтобы сделать ячейку редактируемой и активировать делегат"""
        # снова проверяю, что работаю с пятой колонкой
        if index.column() == 4:
            # делаю ячейку доступной для выбора, активной и редактируемой.
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        return super().flags(index)

    def calculate_folder_size(self, index):
        """Метод для расчёта размера папки"""
        file_path = self.filePath(index.sibling(index.row(), 0))
        if os.path.isdir(file_path):
            # вызываю метод для расчета размера папки
            size = self.get_size_folder(file_path)
            # сохраняю размер в кэше в килобайтах
            self.size_cache[file_path] = f"{size} KB"
            # обновляю данные в модели, чтобы отобразить новый размер.
            self.dataChanged.emit(index.sibling(index.row(), 4), index.sibling(index.row(), 4))

    def get_size_folder(self, path):
        """Метод для расчёта размера папки"""
        total_size = 0
        # прохожу по всем вложенным директориям и файлам в папке.
        for path_dir, name_dir, name_file in os.walk(path):
            # для каждого файла в текущей директории формирую полный путь
            for i in name_file:
                file_path = os.path.join(path_dir, i)
                # если файл существует, то добавляю его размер к общему размеру
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
        return total_size // 1024


class UpdateButtonDelegate(QStyledItemDelegate):
    """Делегат для отображения кнопки "Обновить" или размера папки в ячейке"""

    def paint(self, painter, option, index):
        """Переопределяю метод paint для кастомной отрисовки ячейки"""
        # проверяю снова, что это 5 колонка и директория и получаю полный путь к папке
        if index.column() == 4 and index.model().isDir(index):
            file_path = index.model().filePath(index.sibling(index.row(), 0))
            # получаю размер папки если он уже рассчитан то отрисовываю размер в центре ячейки
            size = index.model().size_cache.get(file_path, "")
            if size:
                painter.save()
                painter.drawText(option.rect, Qt.AlignCenter, size)
                painter.restore()
            else:
                button = QPushButton("Обновить")
                button.resize(option.rect.size())
                painter.save()
                # перемещаю контекст рисования в начало ячейки.
                painter.translate(option.rect.topLeft())
                # отрисовываю кнопку
                button.render(painter)
                painter.restore()
        else:
            super().paint(painter, option,
                          index)

    def editorEvent(self, event, model, option, index):
        """Обработка событий мыши для делегата"""
        # если событие (нажатие мыши), и это пятая колонка, и это директория, то расчитваю размер папки
        if event.type() == event.MouseButtonRelease and index.column() == 4 and index.model().isDir(index):

            model.calculate_folder_size(index)
            return True
        return super().editorEvent(event, model, option,
                                   index)


class DirView(QWidget):
    """Класс основного окна"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Проводник")
        self.resize(1200, 800)

        # реализация модели файловой системы для отображения структуры файлов
        self.model = FileSizeSystemModel()
        # Установка домашней директории текущего юзера
        self.model.setRootPath(QDir.homePath())
        # установка фильтров для отображения всех файлов и папок (включая скрытые)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)

        # реализация древовидного представления (виджет для отображения структуры файловой системы)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        # Установка начальной директории для отображения
        self.tree.setRootIndex(self.model.index(QDir.homePath()))
        # установка сортировки по столбцам
        self.tree.setSortingEnabled(True)

        # настройка столбцов (устанавливаю ширину первой колонки (имя файла или папки))
        self.tree.setColumnWidth(0, 250)
        # Динамическое изменение второй колонки
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        # отображаю колонки ТИП, ДАТА и РАЗМЕР ПАПКИ
        self.tree.setColumnHidden(2, False)
        self.tree.setColumnHidden(3, False)
        self.tree.setColumnHidden(4, False)

        # создаю делегат для кнопки "Обновить" и отображения размера
        delegate = UpdateButtonDelegate()
        # привязываю делегат к 5 колонке
        self.tree.setItemDelegateForColumn(4, delegate)

        # реализация поля для ввода текста поиска
        self.search = QLineEdit()
        self.search.setPlaceholderText("Укажите название файла или папки")
        # сигнал изменения текста к функции фильтрации
        self.search.textChanged.connect(self.filter)

        # макет для размещения виджетов поиска и дерева
        layout = QVBoxLayout()
        layout.addWidget(self.search)
        layout.addWidget(self.tree)
        # установка макета для нового окна
        self.setLayout(layout)

    def filter(self, text):
        """Метод для филтрации папок и файлов по тексту"""
        if text:
            # если текст передан устанавливаю и включаю фильтрацию модели по имени файлов или папок
            self.model.setNameFilters([f"*{text}*"])
            self.model.setNameFilterDisables(False)
        else:
            # и соответственно наоборот
            self.model.setNameFilterDisables(True)


if __name__ == '__main__':
    # Объект приложения
    app = QApplication(sys.argv)
    # Объект окна
    window = DirView()
    window.show()
    sys.exit(app.exec_())
