# Gemini Project: NEMT Scraper

This project is a Python-based web scraper designed to automate the process of finding and analyzing Non-Emergency Medical Transportation (NEMT) jobs from two different broker websites: MTM and Modivcare.

## Project Overview

The scraper is built using the following technologies:

*   **Python**: The core language for the scraper and data analysis scripts.
*   **Playwright**: A modern web automation library used to control the browser, log in to the websites, and extract data.
*   **Pandas**: A powerful data analysis library used to process and store the scraped job data.
*   **SQLite**: A lightweight database used to store the scraped job data.
*   **Shell Scripting**: Used to automate the execution of the scraper and other related tasks.

The project is structured as follows:

*   `scrape_marketplace.py`: The main entry point for the scraper. It controls the entire scraping process for both MTM and Modivcare.
*   `src/scrapers/`: This directory contains the individual scraper classes for each broker.
    *   `broker_a.py`: The scraper for MTM.
    *   `broker_b.py`: The scraper for Modivcare.
*   `database.py`: A module for interacting with the SQLite database.
*   `email_handler.py`: A module for sending email notifications.
*   `analyze_patterns.py`: A script for analyzing the scraped data and generating reports.
*   `generate_map.py`: A script for generating maps based on the scraped job data.
*   `run_bot.sh`: A shell script for running the scraper in an automated fashion.

## Building and Running

### Prerequisites

*   Python 3.x
*   Pip (Python package installer)
*   A virtual environment (recommended)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv nemt_env
    source nemt_env/bin/activate
    ```
3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Scraper

To run the scraper, you can execute the `run_bot.sh` script:

```bash
./run_bot.sh
```

This script will:

1.  Activate the Python virtual environment.
2.  Run the `scrape_marketplace.py` script to scrape the job data.
3.  Run the `analyze_patterns.py` script to analyze the data and send an email report.
4.  Back up the database and code to Google Drive.

### Configuration

The project uses a `.env` file for configuration. You will need to create this file and add the following variables:

```
MTM_USERNAME=<your_mtm_username>
MTM_PASSWORD=<your_mtm_password>
MODIVCARE_USERNAME=<your_modivcare_username>
MODIVCARE_PASSWORD=<your_modivcare_password>
EMAIL_USER=<your_email_address>
EMAIL_PASSWORD=<your_email_password>
```

## Development Conventions

*   The code is written in Python and follows the PEP 8 style guide.
*   The project uses a modular structure, with each component separated into its own file or directory.
*   The scraper uses Playwright's sync API.
*   The project uses a `.gitignore` file to exclude unnecessary files from version control.
