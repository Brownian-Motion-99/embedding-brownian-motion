# %% Packages
import os
import datetime
import json
import hashlib
import numpy as np

from common.db import get_vdb_connection
from embedding import get_all_posts, get_replies, assemble

# %% Global Variables
from dotenv import load_dotenv
load_dotenv()
SNAPSHOT_PATH = os.environ["SNAPSHOT_PATH"]

from common.configuration import SERIES_TITLE, EMBEDDING_MODEL, DIMENSION, EMBEDDING_TASK_TYPE, QUERY_TASK_TYPE

# %% Functions
def create_chunks():
    """
    Creating chunk file
    Saving chunk file in jsonl, each post (with replies) is stored as one line
    
    Parameters
    ----------
    None
    
    Returns
    -------
    None
    
    """
    # post text
    posts = get_all_posts()
    
    # reply text
    replies = {}
    for id in posts.keys():
        replies.update(get_replies(id))
        
    # assembling post body and replies
    embed_list = []
    for _, id in enumerate(posts.keys()):
        embed_text = assemble(posts[id]["content"], replies[id])
        embed_list.append(embed_text)
    
    # save embed text in jsonl
    with open(f"{SNAPSHOT_PATH}/chunks.jsonl", "w", encoding = "utf-8") as f:
        for _, id in enumerate(posts.keys()):
            item = {
                "id": id,
                "text": embed_list[_],
                "timestamp": posts[id]["timestamp"].isoformat(),
                "permalink": posts[id]["permalink"]
            }
            f.write(json.dumps(item, ensure_ascii = False) + "\n")
        print("chunks.jsonl has been saved successfully.")
        
    return None



def create_vectors():
    """
    Creating vectors file
    
    Parameters
    ----------
    None
    
    Returns
    -------
    None
    
    """
    with get_vdb_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT i.id, i.embedding::real[] FROM items i
                JOIN posts p ON i.id = p.id
                GROUP BY i.id, i.embedding, p.timestamp
                ORDER BY p.timestamp DESC
                """
            )
            results    = cur.fetchall()
            ids        = [id[0] for id in results]
            embeddings = [emb[1] for emb in results]
            
            for id, emb in zip(ids, embeddings):
                try:
                    l2 = np.sqrt(np.sum(np.square(np.asarray(emb, dtype = np.float32))))
                    if abs(l2 - 1.) <= 1e-3:
                        pass
                    else:
                        raise ValueError
                except ValueError:
                    print(f"Embedded vector from post {id} was not correctly normalized.")

            embeddings = np.asarray(embeddings, dtype = np.float32)
            np.save(f"{SNAPSHOT_PATH}/vectors.npy", embeddings)
            print("vectors.npy has been saved successfully.")
            
    return None



def create_manifest(format_ver):
    """
    Creating manifest
    
    Parameters
    ----------
    None
    
    Returns
    -------
    None
    
    """
    # version number
    today       = datetime.datetime.today()
    export_date = today.strftime("%Y.%m.%d")
    
    # title
    title = SERIES_TITLE
    
    # embedding configurations
    emb_config = {
        "model": EMBEDDING_MODEL,
        "dimension": DIMENSION,
        "embedding_task_type": EMBEDDING_TASK_TYPE,
    }
    
    # hash values of vectors.npy and chunks.jsonl
    with open(f"{SNAPSHOT_PATH}/vectors.npy", "rb") as f:
        hash_vectors = hashlib.file_digest(f, "sha256").hexdigest()
    
    with open(f"{SNAPSHOT_PATH}/chunks.jsonl", "rb") as f:
        hash_chunks = hashlib.file_digest(f, "sha256").hexdigest()
        
    # assembling the json
    header = {
        "FormatVersion": format_ver,
        "ExportDate": export_date,
        "SeriesTitle": title,
        "EmbeddingConfiguration": emb_config,
        "QueryTaskType": QUERY_TASK_TYPE,
        "VectorsHash": hash_vectors,
        "ChunksHash": hash_chunks,
    }
    
    with open(f"{SNAPSHOT_PATH}/manifest.json", "w", encoding = "utf-8") as f:
        f.write(json.dumps(header, ensure_ascii = False))
        
    print("manifest.json has been saved successfully.")
    
    return None



# %% Main
def main():
    format_ver = 1
    
    create_chunks()
    create_vectors()
    create_manifest(format_ver)


if __name__ == "__main__":
    main()