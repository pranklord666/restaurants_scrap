from . import db

class Article(db.Model):
    __tablename__ = "rss_articles"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Text)
    title = db.Column(db.Text, nullable=False)
    raw_content = db.Column(db.Text)
    summary = db.Column(db.Text)  # Ensure this is present
    keyword = db.Column(db.Text)
    link = db.Column(db.Text, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.Text, default="out")

    __table_args__ = (db.Index('idx_link', 'link'),)

    def __repr__(self):
        return f"<Article {self.title}>"
