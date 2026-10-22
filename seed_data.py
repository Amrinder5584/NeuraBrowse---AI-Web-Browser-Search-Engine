"""Curated starter index so the browser gives useful results even with no internet / API key.
Each tuple: (url, title, description, keywords, category, base_score)."""

SITES = [
    # --- programming ---------------------------------------------------------
    ("https://www.python.org/", "Python.org", "Official home of the Python programming language: downloads, docs and community.", "python programming language download documentation", "programming", 1.0),
    ("https://docs.python.org/3/tutorial/", "The Python Tutorial", "Official step by step tutorial that introduces Python basics, data structures and modules.", "python tutorial learn beginner basics", "programming", 1.0),
    ("https://realpython.com/", "Real Python", "Practical Python tutorials, guides and courses written by working developers.", "python tutorials flask django data science learn", "programming", 0.95),
    ("https://flask.palletsprojects.com/", "Flask Documentation", "Documentation for Flask, a lightweight Python web framework for APIs and websites.", "flask python web backend framework api", "programming", 1.0),
    ("https://developer.mozilla.org/", "MDN Web Docs", "Reference and guides for HTML, CSS and JavaScript from Mozilla.", "html css javascript web frontend reference dom", "programming", 1.0),
    ("https://stackoverflow.com/", "Stack Overflow", "Question and answer community where developers solve coding problems.", "programming questions errors debugging code help", "programming", 0.9),
    ("https://github.com/", "GitHub", "Host, share and collaborate on code with Git repositories and open source projects.", "git code repository open source collaboration version control", "programming", 0.95),
    ("https://www.w3schools.com/", "W3Schools", "Beginner friendly tutorials and examples for web and programming languages.", "html css javascript sql python tutorial beginner", "programming", 0.85),
    ("https://www.geeksforgeeks.org/", "GeeksforGeeks", "Computer science articles, algorithms, data structures and interview preparation.", "algorithms data structures dsa computer science interview", "programming", 0.85),
    ("https://www.freecodecamp.org/", "freeCodeCamp", "Free interactive coding lessons and certifications for web development.", "learn coding web development free course javascript", "programming", 0.9),
    ("https://leetcode.com/", "LeetCode", "Practice coding problems and prepare for technical interviews.", "coding practice problems interview algorithms", "programming", 0.85),
    ("https://react.dev/", "React", "Official documentation for the React library for building user interfaces.", "react javascript frontend ui components", "programming", 0.9),
    ("https://nodejs.org/", "Node.js", "JavaScript runtime for building server side applications and tools.", "nodejs javascript backend server runtime npm", "programming", 0.9),
    ("https://www.sqlite.org/", "SQLite", "Small, fast, self contained SQL database engine used in apps and mobile devices.", "sqlite database sql embedded storage", "database", 1.0),
    ("https://www.postgresql.org/", "PostgreSQL", "Powerful open source relational database system.", "postgresql postgres database sql relational", "database", 0.95),
    ("https://www.mysql.com/", "MySQL", "Popular open source relational database used by many web applications.", "mysql database sql relational web", "database", 0.9),
    ("https://www.mongodb.com/", "MongoDB", "Document oriented NoSQL database for modern applications.", "mongodb nosql database document json", "database", 0.9),
    ("https://docs.pytest.org/", "pytest Documentation", "Guide to writing simple and scalable tests in Python with pytest.", "pytest testing python unit test automation", "testing", 1.0),
    ("https://www.selenium.dev/", "Selenium", "Browser automation framework used for testing web applications.", "selenium testing browser automation web test", "testing", 0.9),
    # --- AI / data science ---------------------------------------------------
    ("https://huggingface.co/", "Hugging Face", "Hub of open machine learning models, datasets and demos.", "ai machine learning models datasets transformers nlp", "ai", 1.0),
    ("https://www.kaggle.com/", "Kaggle", "Data science competitions, datasets and notebooks to practice machine learning.", "kaggle data science datasets machine learning competitions", "ai", 0.95),
    ("https://pytorch.org/", "PyTorch", "Open source deep learning framework for research and production.", "pytorch deep learning neural network ai framework", "ai", 0.95),
    ("https://www.tensorflow.org/", "TensorFlow", "End to end open source platform for machine learning.", "tensorflow machine learning deep learning keras ai", "ai", 0.95),
    ("https://scikit-learn.org/", "scikit-learn", "Simple and efficient Python tools for machine learning and data analysis.", "scikit learn machine learning python classification regression", "ai", 0.95),
    ("https://arxiv.org/", "arXiv", "Free archive of scientific research papers in AI, physics, maths and more.", "research papers science ai preprints maths physics", "science", 0.9),
    ("https://docs.anthropic.com/", "Anthropic Documentation", "Developer documentation for building applications with Claude models and the API.", "claude anthropic api ai llm assistant developer", "ai", 1.0),
    # --- learning --------------------------------------------------------------
    ("https://www.khanacademy.org/", "Khan Academy", "Free lessons in maths, science, computing and more for learners of all ages.", "learn maths science free lessons education school", "education", 0.95),
    ("https://www.coursera.org/", "Coursera", "Online courses and degrees from universities and companies.", "online courses university certificate learn", "education", 0.85),
    ("https://ocw.mit.edu/", "MIT OpenCourseWare", "Free course materials from MIT classes.", "mit free courses lectures university engineering", "education", 0.9),
    ("https://www.wikipedia.org/", "Wikipedia", "Free online encyclopedia written by volunteers.", "encyclopedia knowledge facts history science reference", "reference", 1.0),
    # --- news / science / health ----------------------------------------------
    ("https://www.bbc.com/news", "BBC News", "International news coverage and analysis.", "news world headlines current events", "news", 0.9),
    ("https://www.reuters.com/", "Reuters", "Global news agency with business and world reporting.", "news business world headlines finance", "news", 0.9),
    ("https://www.nasa.gov/", "NASA", "Space exploration news, missions and science from NASA.", "space nasa astronomy rockets planets science", "science", 0.95),
    ("https://www.nature.com/", "Nature", "Leading journal of scientific research and news.", "science research journal biology physics", "science", 0.9),
    ("https://www.who.int/", "World Health Organization", "Global health information, guidance and statistics.", "health medicine disease who public health", "health", 0.95),
    # --- web / tools -----------------------------------------------------------
    ("https://www.w3.org/", "W3C", "Standards body that develops web standards such as HTML and CSS.", "web standards html css accessibility specification", "web", 0.85),
    ("https://developer.chrome.com/", "Chrome for Developers", "Guides about Chrome, DevTools and modern web platform features.", "chrome browser devtools web performance extensions", "web", 0.85),
    ("https://www.mozilla.org/firefox/", "Mozilla Firefox", "Open source web browser focused on privacy.", "firefox browser privacy mozilla", "web", 0.8),
    ("https://owasp.org/", "OWASP", "Community project that publishes web application security guidance.", "security owasp web vulnerabilities xss sql injection", "security", 0.95),
    ("https://www.draw.io/", "draw.io", "Free online diagramming tool for flowcharts, UML and ER diagrams.", "diagram flowchart uml er diagram design tool", "tools", 0.8),
]
