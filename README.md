# Instagram Groupchat Analysis
An interactive tool for analyzing and visualizing Instagram groupchat data. 


### Installation
1. Clone the repository: `git clone https://github.com/jasonjewelljason/instagram-groupchat-analysis`
2. Install the required packages: `pip install -r requirements.txt`

### Usage
1. [Download your Instagram data,](https://help.instagram.com/181231772500920) and make sure to select HTML format. This might take a few days to process, and you will receive an email when it is ready to download.
2. From your downloaded Instagram data, find the html file(s) for the groupchat you want to analyze. Copy the html files into the `data` folder of this repository. 
3. Run `python html_parser.py`. This will parse the html files, and save the groupchat data as csv files in the `parsed_data` folder.
4. Run `python gui.py` to launch the tool.

### GUI Documentation
The GUI is divided into three tabs:
1. **Overview** - Displays general information about the groupchat, including its title, the total number of messages, and the number of messages sent by each member. It also includes a searchable table of all messages. There are a few functional buttons on this tab:
    - **Load Messages** - By default, the groupchat stored in `parsed_data` will be loaded. If you want to load a different groupchat, click this button and select the directory containing the groupchat's csv files.
    - **Rename Authors** - Useful if authors have changed their display names since the groupchat was created. Click this button to open a window where you can rename authors.
2. **Analysis** - Generates tables based on the type of analysis that the user selects. These tables can be saved as CSV using the **Export** button. As of now, there are two analysis types (but I intend on adding more!):
    - **Author Stats** - Includes many options of statistics to calculate for each author. The user can select which statistics to calculate, and the results will be displayed in a table.
    - **Word Counts By Author** - The user can enter a list of words, and the number of times each word was used by each author will be displayed in a table.
3. **Graphs** - Creates visualizations of the groupchat data. The user can select which graph to create, and the graph will be displayed in the window. The user can then save the graph as an image using the **Export** button. These are the graph options:
    - **Messages per User** - A bar graph showing the number of messages sent by each author.
    - **Activity Over Time** - The user selects a time interval (day, week, month, or year), and chooses which authors to include. The graph will show the number of messages sent by each author during each time interval, to track relative activity over time.
    - **Activity Heatmap** - Shows how active the groupchat is at different times throughout the week.

### License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Contact
Feel free to reach out with any questions or comments!

Jason Jewell - jewell@u.northwestern.edu