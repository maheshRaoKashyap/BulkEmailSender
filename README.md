1. Clone the project
cd C:\Users\mahes\OneDrive\Documents\Practice
git clone https://github.com/YOUR_USERNAME/job-email-sender.git
cd job-email-sender
2. Create virtual environment
python -m venv .venv
3. Install dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

If you don't have requirements.txt:

.\.venv\Scripts\python.exe -m pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
4. Copy your private files

Put these manually inside the project:

credentials.json
token.json
recipients.csv
resume.pdf

Don't upload them to GitHub.

5. Check CSV
email
your-email@gmail.com
6. Run
.\.venv\Scripts\python.exe app.py
7. First test

Keep:

TEST_MODE = True
MAX_EMAILS_PER_RUN = 1

Then type:

SEND
8. Check results
Get-Content .\logs\sending_status.csv

That's it.
