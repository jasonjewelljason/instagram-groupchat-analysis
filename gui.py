import sys
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QTableView, QPushButton, QVBoxLayout, QWidget, 
                               QLineEdit, QLabel, QTabWidget, QHBoxLayout, QComboBox, QFileDialog,
                               QCheckBox, QPushButton, QDialog, QDialogButtonBox, QListWidget)
from PySide6.QtCore import Qt, QAbstractTableModel
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from html_parser import load_df
from analysis import (activity_over_time, format_x_labels_universal, detect_time_period, generate_author_stats, count_words_by_author)
import seaborn as sns
import unicodedata

def clean_string(s):
    # unused for now
    # Normalize Unicode data
    s = unicodedata.normalize('NFKD', s)
    # Remove non-printable characters and any leading special characters (e.g., emojis)
    s = ''.join(ch for ch in s if unicodedata.category(ch)[0] not in ['C', 'So'])
    # Strip leading and trailing whitespace
    s = s.strip()
    return s

class GroupChatAnalyzer(QMainWindow):
    def __init__(self, directory):
        super().__init__()

        self.setWindowTitle("Instagram Group Chat Analyzer")
        self.setGeometry(100, 100, 1000, 700)

        self.initUI()
        if directory:
            self.directory = directory
            self.loadMessages(directory=directory)

    def initUI(self):
        # Tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab 1: Overview
        self.tab1 = QWidget()
        self.initTab1()
        self.tabs.addTab(self.tab1, "Overview")

        # Tab 2: Analysis
        self.tab2 = QWidget()
        self.initTab2()
        self.tabs.addTab(self.tab2, "Analysis")

        # Tab 3: Graphs
        self.tab3 = QWidget()
        self.initTab3()
        self.tabs.addTab(self.tab3, "Graphs")

    def initTab1(self):
        layout = QVBoxLayout(self.tab1)

        # Load messages button
        loadButton = QPushButton("Load Messages")
        loadButton.clicked.connect(self.loadMessages)
        layout.addWidget(loadButton)

        # Rename authors button
        renameButton = QPushButton("Rename Authors")
        renameButton.clicked.connect(self.openRenameDialog)
        layout.addWidget(renameButton)

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

    def openRenameDialog(self):
        # Lets you rename authors multiple times
        dialog = RenameDialog(self)

        # Create a "Finished" button
        finished_button = QPushButton("Finished", dialog)
        finished_button.clicked.connect(dialog.reject)  # Close the dialog when the button is clicked
        dialog.layout().addWidget(finished_button)  # Add the button to the dialog's layout

        while dialog.exec():
            old_name = dialog.getOldName()
            new_name = dialog.getNewName()
            if old_name and new_name and new_name != old_name:
                self.groupchat.rename_author(old_name, new_name)
                self.extractVariablesFromGroupchat()
                self.tableView.setModel(PandasModel(self.messages))
                self.tableView.resizeColumnsToContents()
                self.updateStatistics()
                print(self.groupchat.authors)
                print(self.authors)
                
                # Update the list of authors in the dialog's listbox
                dialog.listbox.clear()
                dialog.listbox.addItems(self.groupchat.authors)
                dialog.entry.setText(new_name)


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
        self.resultsTable.resizeColumnsToContents()

    def exportResults(self):
        # Export results to csv
        selected_file, _ = QFileDialog.getSaveFileName(self, "Save Results", "", "CSV Files (*.csv)")
        if selected_file:
            self.resultsTable.model()._data.to_csv(selected_file, index=False)

    def initTab3(self):
        layout = QHBoxLayout(self.tab3)

        # Graph type selection

        button_layout = QVBoxLayout()
        button_layout.addStretch(1)

        messagesperuserButton = QPushButton("Messages per User")
        messagesperuserButton.clicked.connect(lambda: self.updateGraph("Messages per User"))
        button_layout.addWidget(messagesperuserButton)

        activityovertimeButton = QPushButton("Activity Over Time")
        activityovertimeButton.clicked.connect(lambda: self.openActivityOverTimeDialog())
        button_layout.addWidget(activityovertimeButton)

        heatmapButton = QPushButton("Activity Heatmap")
        heatmapButton.clicked.connect(lambda: self.updateGraph("Activity Heatmap"))
        button_layout.addWidget(heatmapButton)

        button_layout.addStretch(1)

        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget)

        # Graph display area
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Export button
        exportButton = QPushButton("Export")
        exportButton.clicked.connect(self.exportGraph)
        layout.addWidget(exportButton)

    def loadMessages(self, directory=None):
        # Load messages from folder containing csv files
        if not directory:
            selected_directory = QFileDialog.getExistingDirectory()
        else:
            selected_directory = directory
        self.groupchat = load_df(selected_directory)
        self.extractVariablesFromGroupchat()
        self.messages['content'].fillna("", inplace=True)
        self.tableView.setModel(PandasModel(self.groupchat.messages))
        self.tableView.resizeColumnsToContents()
        self.updateStatistics()
        
    def extractVariablesFromGroupchat(self):
        # Extract variables from the groupchat
        self.messages = self.groupchat.messages
        self.likes = self.groupchat.likes
        self.authors = self.groupchat.authors
        self.title = self.groupchat.title

    def searchMessages(self, text):
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
            ax.figure.tight_layout()
            self.canvas.draw()
        elif graphType == "Activity Over Time":
            self.plot_activity_over_time(self.figure, self.groupchat)
            self.canvas.draw()
        elif graphType == "Activity Heatmap":
            self.plot_activity_heatmap(self.figure, self.groupchat)
            self.canvas.draw()

    def exportGraph(self):
        selected_file, _ = QFileDialog.getSaveFileName(self, "Save Graph", "", "PNG Files (*.png)")
        if selected_file:
            self.figure.savefig(selected_file)

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

        fig.tight_layout()
        fig.subplots_adjust(left=0.15, right=0.9, top=0.9, bottom=0.1)
        
    def plot_activity_heatmap(self, fig, groupchat):
        # Clear the existing figure and create a new axes
        fig.clear()
        ax = fig.add_subplot(111)

        m = groupchat.messages

        # Convert 'timestamp' to datetime
        m['timestamp'] = pd.to_datetime(m['timestamp'])

        # Extract day of week and hour from 'timestamp'
        m['day_of_week'] = m['timestamp'].dt.dayofweek
        m['hour_of_day'] = m['timestamp'].dt.hour

        # Prepare data for heatmap
        # Group the data by day of week and hour of day and count the messages
        heatmap_data = m.groupby(['day_of_week', 'hour_of_day']).size().unstack(fill_value=0)

        # Plot the heatmap on the specified axes
        sns.heatmap(heatmap_data, cmap='YlGnBu', annot=False, ax=ax)

        ax.set_title('Activity Heatmap')
        ax.set_xlabel('Hour of Day')
        ax.set_ylabel('Day of Week (0: Monday - 6: Sunday)')
        fig.tight_layout()

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

    def openActivityOverTimeDialog(self):
        dialog = ActivityOverTimeDialog(self)
        if dialog.exec():
            period = dialog.getPeriod()
            authors = dialog.getAuthors()
            self.performActivityOverTimeAnalysis(period, authors)

    def performActivityOverTimeAnalysis(self, period, authors):
        self.plot_activity_over_time(self.figure, self.groupchat, period=period, authors=authors)
        self.canvas.draw()
        

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
            value = self._data.iloc[index.row(), index.column()]
            if isinstance(value, float):
                return format(value, '.3f')
            return str(value)
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

class ActivityOverTimeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activity Over Time Options")
        layout = QVBoxLayout(self)

        # Label for period selection
        layout.addWidget(QLabel("Select time period:"))

        # Period selection combobox
        self.periodComboBox = QComboBox()
        self.periodComboBox.addItems(['Year', 'Month', 'Week', 'Day'])
        layout.addWidget(self.periodComboBox)

        # Label for author selection
        layout.addWidget(QLabel("Select authors:"))

        # Store checkboxes in a dictionary for easy access
        self.checkboxes = {}
        for author in self.parent().authors:
            self.checkboxes[author] = QCheckBox(author)
            layout.addWidget(self.checkboxes[author])

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

    def getPeriod(self):
        return self.periodComboBox.currentText()[0]
    
    def getAuthors(self):
        # Return a list of selected authors
        return [author for author, cb in self.checkboxes.items() if cb.isChecked()]

class RenameDialog(QDialog):
    # Dialog for renaming authors. Displays a list of authors and allows the user to select one and enter a new name, which will be applied to all messages and likes by that author, and also dynamically update the list of authors.
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Rename Author")
        layout = QVBoxLayout(self)

        # List of authors
        layout.addWidget(QLabel("Select author to rename:"))
        self.listbox = QListWidget()
        self.listbox.addItems(self.parent().authors)
        self.listbox.itemSelectionChanged.connect(self.on_listbox_select)  # Connect the signal to the method
        layout.addWidget(self.listbox)

        # Label and input field for new name
        layout.addWidget(QLabel("Enter new name:"))
        self.entry = QLineEdit()
        layout.addWidget(self.entry)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def getOldName(self):
        return self.listbox.currentItem().text()

    def getNewName(self):
        return self.entry.text().strip()

    def on_listbox_select(self):
        selected_author = self.listbox.currentItem().text()
        self.entry.setText(selected_author)  # Set the text of the entry box to the selected author
    

if __name__ == '__main__':
    from stylesheet import stylesheet, darkmodestylesheet
    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet())
    app.setFont(QFont('Segoe UI', 10))
    ex = GroupChatAnalyzer('datatest2')
    ex.show()
    sys.exit(app.exec())
