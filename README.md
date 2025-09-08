# Trakt to Serializd Migration Script

## Project Overview

This project is a **Trakt to Serializd Migration Script** designed to automate the migration of watched shows data from a Trakt account to a Serializd account. It is built especially for Termux environments with robust error handling and API rate limiting to ensure reliable and efficient migration of user watch history.

## Key Features

- OAuth device authentication flow for secure Trakt API access.
- Email/password authentication for Serializd API.
- Retrieval of watched shows and episodes from Trakt.
- Lookup and logging of corresponding shows and episodes on Serializd.
- Ability to mark entire seasons or individual episodes as watched.
- Rate limiting to avoid API request throttling.
- Detailed logging of migration progress and errors.
- Interactive command-line interface for user authentication and migration control.
- Compatible with Python 3.6+ and Termux.

## Installation

1. Clone or download the project files.
2. Ensure Python 3.6 or higher is installed.
3. Install dependencies via pip:

   ```
   pip install requests
   ```

4. Create a Trakt API application at [Trakt OAuth Applications](https://trakt.tv/oauth/applications/new) with redirect URI `urn:ietf:wg:oauth:2.0:oob`.
5. Have your Serializd email and password ready.

## Dependencies

- Python 3.6+
- `requests` library

Install dependencies:

```
pip install requests
```

## Usage

Run the script from the command line:

```
python trakt_to_serializd_migrator_fixed.py
```

Follow the prompts to:

- Authenticate with Trakt using the device code flow.
- Login to your Serializd account with email and password.
- Confirm and start migrating your watched shows and episodes.
- Check the console and `migration.log` for detailed progress.

### Example Workflow

1. Start the script.
2. Authenticate with Trakt (visit URL, enter code).
3. Enter your Serializd credentials.
4. Confirm migration start.
5. Monitor progress via console output and log file.

## Contributing

Contributions are welcome! Please:

- Report bugs or suggest features by opening issues.
- Fork the repository and create feature branches.
- Commit changes with clear messages.
- Push to your branch and open a pull request.

Ensure code follows best practices and includes appropriate error handling and logging.

## License

This project is licensed under the MIT License. See the LICENSE file for details.