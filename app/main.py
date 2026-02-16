from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
import shutil
import os

from . import models, database

# Create the database tables if they don't exist
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

@app.post("/upload/")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    file_location = f"uploads/{file.filename}"
    
    # 1. Save the actual file
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    # 2. Save the metadata to PostgreSQL
    new_doc = models.Document(filename=file.filename, file_path=file_location)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    return {"id": new_doc.id, "filename": new_doc.filename, "status": "Saved to DB"}