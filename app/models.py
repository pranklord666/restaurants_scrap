from . import db

class Article(db.Model):
    __tablename__ = "rss_articles"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50))
    title = db.Column(db.Text, nullable=False)
    raw_content = db.Column(db.Text)
    summary = db.Column(db.Text)
    keyword = db.Column(db.Text)
    link = db.Column(db.Text, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.String(10), default="out")

    def __repr__(self):
        return f"<Article {self.title}>"
