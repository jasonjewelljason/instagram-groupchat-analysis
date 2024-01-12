import sys
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QTableView, QPushButton, QVBoxLayout, QWidget, 
                               QLineEdit, QLabel, QTabWidget, QHBoxLayout, QComboBox, QTextEdit, QFileDialog,
                               QCheckBox, QPushButton, QGridLayout, QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, QAbstractTableModel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from html_parser import load_df
from analysis import (activity_over_time, format_x_labels_universal, detect_time_period, generate_author_stats,
                      count_words_by_author)

class GroupChatAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Instagram Group Chat Analyzer")
        self.setGeometry(100, 100, 1000, 700)

        self.initUI()

    def initUI(self):
        # Tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab 1: Basic Statistics & Search
        self.tab1 = QWidget()
        self.initTab1()
        self.tabs.addTab(self.tab1, "Statistics & Search")

        # Tab 2: Analysis Options
        self.tab2 = QWidget()
        self.initTab2()
        self.tabs.addTab(self.tab2, "Custom Analysis")

        # Tab 3: Graphical Representations
        self.tab3 = QWidget()
        self.initTab3()
        self.tabs.addTab(self.tab3, "Graphs")

    def initTab1(self):
        layout = QVBoxLayout(self.tab1)

        # Load messages button
        loadButton = QPushButton("Load Messages")
        loadButton.clicked.connect(self.loadMessages)
        layout.addWidget(loadButton)

        # Search bar
        searchBar = QLineEdit()
        searchBar.setPlaceholderText("Search messages...")
        searchBar.textChanged.connect(self.searchMessages)
        layout.addWidget(searchBar)

        # Messages table
        self.tableView = QTableView()
        layout.addWidget(self.tableView)

        # Statistics label
        self.statsLabel = QLabel("Statistics will appear here")
        layout.addWidget(self.statsLabel)

    def initTab2(self):
        layout = QVBoxLayout(self.tab2)

        # Button for 'Author Stats' Analysis
        authorStatsButton = QPushButton("Author Stats")
        authorStatsButton.clicked.connect(self.openAuthorStatsDialog)
        layout.addWidget(authorStatsButton)

        # Button for 'Word Counts by Author' Analysis
        wordCountButton = QPushButton("Word Counts by Author")
        wordCountButton.clicked.connect(self.openWordCountDialog)
        layout.addWidget(wordCountButton)

        # Results display area (as a table)
        self.resultsTable = QTableView()
        layout.addWidget(self.resultsTable)

        # Export button
        exportButton = QPushButton("Export")
        exportButton.clicked.connect(self.exportResults)
        layout.addWidget(exportButton)

    def displayAnalysis(self, results_df):
        # Display results in the table
        self.resultsTable.setModel(PandasModel(results_df))

    def exportResults(self):
        # Export results to csv
        selected_file, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "CSV Files (*.csv)")
        if selected_file:
            self.resultsTable.model()._data.to_csv(selected_file, index=False)

    def initTab3(self):
        layout = QHBoxLayout(self.tab3)

        # Graph type selection
        self.graphComboBox = QComboBox()
        self.graphComboBox.addItems(["Select Graph Type", "Messages per User", "Activity Over Time"])
        self.graphComboBox.currentTextChanged.connect(self.updateGraph)
        layout.addWidget(self.graphComboBox)

        # Graph display area
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

    def loadMessages(self):
        # Load messages from folder containing csv files
        selected_directory = QFileDialog.getExistingDirectory()
        self.groupchat = load_df(selected_directory)
        self.messages = self.groupchat.messages
        self.likes = self.groupchat.likes
        self.authors = self.groupchat.authors
        self.title = self.groupchat.title
        self.tableView.setModel(PandasModel(self.groupchat.messages))
        self.updateStatistics()
        

    def searchMessages(self, text):
        # TODO: fix
        if text:
            filtered_df = self.messages[self.messages['content'].str.contains(text, case=False)]
            self.tableView.setModel(PandasModel(filtered_df))
        else:
            self.tableView.setModel(PandasModel(self.messages))

    def updateStatistics(self):
        message_counts = self.messages['author'].value_counts()
        self.statsLabel.setText(f"Total Messages: {len(self.messages)}\nMessages per User:\n{message_counts}")

    def updateGraph(self, graphType):
        if graphType == "Messages per User":
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            message_counts = self.messages['author'].value_counts()
            ax.bar(message_counts.index, message_counts.values)
            ax.set_xlabel('User')
            ax.set_ylabel('Number of Messages')
            ax.set_title('Messages per User')
            self.canvas.draw()
        elif graphType == "Activity Over Time":
            self.plot_activity_over_time(self.figure, self.groupchat)
            self.canvas.draw()

    def plot_activity_over_time(self, fig, groupchat, period='M', authors='all', label_frequency=4):
        # Clear the existing figure and create a new axes
        fig.clear()
        ax = fig.add_subplot(111)

        activity_data = activity_over_time(groupchat, period)

        if authors == 'all':
            data_to_plot = activity_data.sum(axis=1)
        elif authors is not None:
            data_to_plot = activity_data[authors]
        else:
            data_to_plot = activity_data

        period = detect_time_period(data_to_plot.index)
        labels = format_x_labels_universal(index=data_to_plot.index, period=period)

        # Reducing the frequency of labels to avoid crowding
        for i in range(len(labels)):
            if i % label_frequency != 0 and period != 'Y':
                labels[i] = ''

        # Plotting using the ax object
        data_to_plot.plot(kind='bar', ax=ax, figsize=(15, 7))

        ax.set_title('Activity Over Time')
        ax.set_xlabel('Time Period')
        ax.set_ylabel('Number of Messages')

        # Set the custom labels with reduced frequency
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45)

        if authors != 'all':
            ax.legend(title='Authors')

        ax.figure.tight_layout()

    def openWordCountDialog(self):
        dialog = WordCountDialog(self)
        if dialog.exec():
            words = dialog.getWords()
            self.performWordCountAnalysis(words)

    def performWordCountAnalysis(self, words):
        # Split words and perform analysis
        word_list = [word.strip() for word in words.split(',')]
        # Now perform your analysis with word_list
        results_df = count_words_by_author(self.groupchat, word_list).reset_index()
        self.displayAnalysis(results_df)

    def openAuthorStatsDialog(self):
        columns = ['Total sends', 'Likes given', 'Likes received', 'Word count', 'Average sentiment', 'Total runs', 'Longest run', 'Average run length', 'Total messages', 'Total links', 'Total images', 'Total posts', 'Total videos', 'Total audios']
        dialog = AuthorStatsDialog(self, columns=columns)
        if dialog.exec():
            selected_columns = dialog.getColumns()
            self.performAuthorStatsAnalysis(selected_columns)

    def performAuthorStatsAnalysis(self, columns):
        results_df = generate_author_stats(self.groupchat, columns).reset_index()
        self.displayAnalysis(results_df)
        

class PandasModel(QAbstractTableModel):
    def __init__(self, df):
        QAbstractTableModel.__init__(self)
        self._data = df

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._data.columns[section]
        return None

class WordCountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Word Count Options")
        layout = QVBoxLayout(self)

        # Label and input field for word count
        layout.addWidget(QLabel("Enter words (separated by commas):"))
        self.wordInput = QLineEdit()
        layout.addWidget(self.wordInput)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def getWords(self):
        return self.wordInput.text()

class AuthorStatsDialog(QDialog):
    def __init__(self, parent=None, columns=None):
        super().__init__(parent)
        self.setWindowTitle("Author Stats Options")
        layout = QVBoxLayout(self)

        # Label for column selection
        layout.addWidget(QLabel("Include columns:"))

        # Store checkboxes in a dictionary for easy access
        self.checkboxes = {}
        for column in columns:
            self.checkboxes[column] = QCheckBox(column)
            layout.addWidget(self.checkboxes[column])

        # Select All button
        self.selectAllButton = QPushButton("Select All")
        self.selectAllButton.clicked.connect(self.selectAll)
        layout.addWidget(self.selectAllButton)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selectAll(self):
        # Toggle the state of all checkboxes
        all_checked = all(cb.isChecked() for cb in self.checkboxes.values())
        for cb in self.checkboxes.values():
            cb.setChecked(not all_checked)

    def getColumns(self):
        # Return a list of selected columns
        return [column for column, cb in self.checkboxes.items() if cb.isChecked()]

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = GroupChatAnalyzer()
    ex.show()
    sys.exit(app.exec())
