from app import create_app

app = create_app()

if __name__ == '__main__':
    # This condition is unnecessary in production (Render uses Gunicorn)
    app.run(debug=False, host='0.0.0.0', port=5000)