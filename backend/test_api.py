"""
Sample test script to demonstrate API usage
Run after starting the server
"""
import requests
import json


def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check endpoint...")
    response = requests.get("http://localhost:8000/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def test_analyze_sample():
    """Test report analysis with sample text"""
    print("This is a sample test file.")
    print("To test the actual API:")
    print()
    print("1. Start the server: python main.py")
    print("2. Use curl or Postman to upload a file:")
    print()
    print("curl -X POST http://localhost:8000/api/analyze-report \\")
    print('  -F "file=@your_lab_report.pdf"')
    print()
    print("Or use the interactive docs: http://localhost:8000/docs")


if __name__ == "__main__":
    print("=" * 60)
    print("MedReport AI - API Test")
    print("=" * 60)
    print()

    try:
        test_health_check()
        test_analyze_sample()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server")
        print("Make sure the server is running: python main.py")
