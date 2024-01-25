def stylesheet():
    return """
    QMainWindow {
        font-family: 'Arial';  /* Arial can be a good alternative */
        font-size: 10pt;
        background-color: #FAFAFA;  /* A light background color */
    }
    QPushButton {
        background-color: white;  /* White interior */
        color: #0078D7;  /* Blue text color */
        border-radius: 5px;
        padding: 5px;
        border: 2px solid #0078D7;  /* Blue border */
    }
    QPushButton:hover {
        background-color: #E6F0FA;  /* Light blue background for hover effect */
        color: #0053A6;  /* Darker blue text color on hover */
        border: 2px solid #0053A6;  /* Darker blue border on hover */
    }
    QLabel, QTableView, QTabWidget, QLineEdit, QComboBox, QTextEdit {
        color: #333;  /* Dark text for better readability */
    }
    QTabWidget::pane {
        border: 0;
    }
    QTabBar::tab {
        background: #D9D9D9; 
        color: white;
        padding: 5px;
    }
    QTabBar::tab:selected {
        background: #0078D7;
    }
    QTableView {
        selection-background-color: #0078D7;  
        selection-color: white;
    }
    QLineEdit, QTextEdit, QComboBox {
        border: 1px solid #ddd;
        padding: 2px;
    }
    FigureCanvasQTAgg {
        border: 2px solid black;
        border-radius: 5px;
    }
"""

def darkmodestylesheet():
    return """
    QMainWindow {
        font-family: 'Segoe UI';  /* Arial can be a good alternative */
        font-size: 10pt;
        background-color: #2D2D2D;  /* Dark background for the main window */
    }
    QPushButton {
        background-color: #3C3C3C;  /* Darker shade for buttons */
        color: #DADADA;  /* Light text color for readability */
        border-radius: 5px;
        padding: 5px;
        border: 2px solid #3C3C3C;  /* Border color similar to the button background */
    }
    QPushButton:hover {
        background-color: #505050;  /* Slightly lighter shade for hover effect */
        color: #FFFFFF;  /* White text color on hover */
        border: 2px solid #606060;  /* Slightly lighter border on hover */
    }
    QLabel, QLineEdit, QTextEdit, QComboBox {
        color: #DADADA;  /* Light color text for readability */
    }
    QTabWidget::pane {
        border: 0;
    }
    QTabBar::tab {
        background: #3C3C3C;
        color: #DADADA;
        padding: 5px;
    }
    QTabBar::tab:selected {
        background: #505050;
        color: #FFFFFF;
    }
    QTableView, QListWidget {
        background-color: #2D2D2D;
        color: #DADADA;
        border: 1px solid #3C3C3C;
        gridline-color: #3C3C3C;
    }
    QTableView::item:selected, QListWidget::item:selected {
        background-color: #505050;
    }
    QLineEdit, QTextEdit, QComboBox {
        border: 1px solid #3C3C3C;
        background-color: #2D2D2D;
        color: #DADADA;
    }
    QHeaderView::section {
        background-color: #3C3C3C;
        padding: 4px;
        border: 1px solid #4C4C4C;
        color: #DADADA;
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        border: 1px solid #2D2D2D;
        background: #3C3C3C;
        width: 15px;
        margin: 15px 3px 15px 3px;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #505050;
        min-height: 20px;
        min-width: 20px;
    }
    QScrollBar::add-line, QScrollBar::sub-line {
        background: #3C3C3C;
    }
"""

