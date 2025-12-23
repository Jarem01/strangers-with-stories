from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db, engine, Base, Story
from models import StoryCreate, StoryResponse, StoryAdmin
from better_profanity import profanity
import random

# Create tables on startup
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Strangers with Stories")

# Initialize profanity filter
profanity.load_censor_words()

# Allow CORS for your frontend (adjust later for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local dev; restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="public"), name="static")

ALLOWED_CATEGORIES = ["Love", "Wisdom", "Regret", "Joy", "Pain", "Change", "Other"]


# ===== FILE SERVING =====

def is_legitimate_story(text: str) -> bool:
    """
    Basic check for gibberish/spam stories.
    Returns False if story looks like spam.
    """
    # Must be at least 10 characters (already validated in models, but double-check)
    if len(text.strip()) < 10:
        return False
    
    # Check for excessive repeated characters (e.g., "aaaaaaa" or "!!!!!!!")
    for char in text:
        if text.count(char) > len(text) * 0.3:  # More than 30% same character
            return False
    
    # Check for too many non-alphabetic characters (spam often has lots of symbols)
    non_alpha = sum(1 for c in text if not c.isalnum() and c not in ' .,!?;:\'"—–-')
    if non_alpha > len(text) * 0.2:  # More than 20% non-standard symbols
        return False
    
    # Check if it's mostly gibberish (words that are too long with no vowels)
    words = text.split()
    gibberish_count = 0
    for word in words:
        # A real word usually has vowels and isn't too long
        vowels = sum(1 for c in word.lower() if c in 'aeiou')
        if len(word) > 8 and vowels == 0:  # Long word with no vowels = probably gibberish
            gibberish_count += 1
    
    if gibberish_count > len(words) * 0.3:  # More than 30% gibberish words
        return False
    
    return True

@app.get("/")
def read_root():
    return FileResponse("public/index.html")

@app.get("/admin")
def admin_dashboard():
    return FileResponse("public/admin.html")


# ===== PUBLIC ENDPOINTS =====


@app.get("/api/stories", response_model=list[StoryResponse])
def get_public_stories(
    category: str = Query(None),
    db: Session = Depends(get_db)
):
    """Get all approved stories, optionally filtered by category"""
    query = db.query(Story).filter(Story.approved == True).order_by(Story.created_at.desc())
    
    if category:
        if category not in ALLOWED_CATEGORIES:
            raise HTTPException(status_code=400, detail="Invalid category")
        query = query.filter(Story.category == category)
    
    return query.all()

@app.get("/api/stories/random")
def get_random_story(db: Session = Depends(get_db)):
    """Get a random approved story"""
    stories = db.query(Story).filter(Story.approved == True).all()
    
    if not stories:
        raise HTTPException(status_code=404, detail="No approved stories yet")
    
    random_story = random.choice(stories)
    
    # Manually construct the response to avoid serialization issues
    return {
        "id": random_story.id,
        "title": random_story.title,
        "author_name": random_story.author_name,
        "story_text": random_story.story_text,
        "category": random_story.category,
        "created_at": random_story.created_at,
        "approved": random_story.approved
    }

@app.get("/api/stories/{story_id}", response_model=StoryResponse)
def get_story(story_id: int, db: Session = Depends(get_db)):
    """Get a single approved story"""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.approved == True
    ).first()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    return story


@app.post("/api/stories", response_model=dict)
def create_story(story: StoryCreate, db: Session = Depends(get_db)):
    """Submit a new story"""
    if story.category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    # NEW: Check for profanity
    if profanity.contains_profanity(story.story_text):
        raise HTTPException(
            status_code=400, 
            detail="Your story contains inappropriate language. Please revise and resubmit."
        )
    
    # NEW: Check for spam/gibberish (very short words repeated, all caps, etc.)
    if not is_legitimate_story(story.story_text):
        raise HTTPException(
            status_code=400,
            detail="Your submission doesn't look like a real story. Please try again."
        )
    
    db_story = Story(
        title=story.title,
        author_name=story.author_name,
        author_email=story.author_email,
        story_text=story.story_text,
        category=story.category,
        approved=False
    )
    
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    
    return {"id": db_story.id, "message": "Story submitted for review"}



# ===== ADMIN ENDPOINTS =====


@app.get("/api/admin/stories", response_model=list[StoryAdmin])
def get_pending_stories(db: Session = Depends(get_db)):
    """Get all stories (pending + approved) for admin review"""
    return db.query(Story).order_by(Story.created_at.desc()).all()


@app.patch("/api/admin/stories/{story_id}/approve")
def approve_story(story_id: int, db: Session = Depends(get_db)):
    """Approve a story"""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story.approved = True
    story.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Story approved"}


@app.delete("/api/admin/stories/{story_id}")
def reject_story(story_id: int, db: Session = Depends(get_db)):
    """Reject/delete a story"""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    db.delete(story)
    db.commit()
    
    return {"message": "Story deleted"}


@app.get("/api/health")
def health_check():
    """Simple health check"""
    return {"status": "ok"}
