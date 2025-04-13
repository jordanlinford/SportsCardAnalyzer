# Sports Card Analyzer Pro

A comprehensive sports card collection management and analysis application built with Streamlit.

## Features

- 🔐 User Authentication
- 📊 Market Analysis
- 📋 Collection Management
- 🔄 Trade Analysis
- 📸 Display Case
- 👤 Profile Management

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/SportsCardAnalyzer-6.git
   cd SportsCardAnalyzer-6
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.streamlit.txt
   ```

4. **Environment Setup**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`:
     ```bash
     cp .streamlit/secrets.toml.example .streamlit/secrets.toml
     ```
   - Fill in your Firebase credentials in `.env`:
     - Get your Firebase Web App configuration from Firebase Console > Project Settings > General > Your Apps > Web App
     - Get your Firebase Service Account credentials from Firebase Console > Project Settings > Service Accounts
     - Replace all placeholder values in `.env` with your actual credentials
   - Fill in your Streamlit secrets in `.streamlit/secrets.toml`:
     - Copy relevant values from your `.env` file to `.streamlit/secrets.toml`
     - Ensure all sensitive data is properly formatted

5. **Run the Application**
   ```bash
   streamlit run app.py
   ```

## Deployment

### Local Deployment
1. Follow the setup instructions above
2. Run `streamlit run app.py`
3. Access the app at `http://localhost:8501`

### Streamlit Cloud Deployment
1. **Prerequisites**
   - Create a Streamlit Cloud account at https://streamlit.io/cloud
   - Connect your GitHub account
   - Ensure your repository is public or you have a Streamlit Cloud Teams account

2. **Configure Deployment**
   - Go to https://share.streamlit.io/
   - Click "New app"
   - Select your repository
   - Configure the following settings:
     - Main file path: `app.py`
     - Branch: `main` (or your preferred branch)
     - Python version: `3.9` or higher

3. **Environment Variables**
   - In the Streamlit Cloud dashboard, go to "Advanced settings"
   - Add all environment variables from your `.env` file
   - Add all secrets from your `.streamlit/secrets.toml` file
   - Ensure sensitive data is properly formatted

4. **Deploy**
   - Click "Deploy"
   - Wait for the deployment to complete
   - Access your app at the provided URL

### Deployment Notes
- The app uses `.streamlit/cloud.toml` for deployment configuration
- Memory and CPU requirements are set in the cloud configuration
- Health checks are configured to ensure app availability
- Environment variables are managed through Streamlit Cloud's dashboard

## Development

- Run tests: `python -m pytest tests/`
- Format code: `black .`
- Check linting: `flake8 .`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 