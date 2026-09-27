# %% Packages
import numpy as np

from google import genai
from google.genai.types import EmbedContentConfig

from common.db import get_vdb_connection

# %% Global Variables
from common.configuration import EMBEDDING_MODEL, EMBEDDING_TASK_TYPE, DIMENSION

# %% Functions
def get_all_posts():
    """
    Fetching all posts from database except for 停更
    
    Parameters
    ----------
    cur: psycopg.Cursor
        database cursor
        
    Returns
    -------
    posts: dict
        post dictionary containing id, text and timestamp
        
    """
    with get_vdb_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.text, p.timestamp, p.permalink FROM posts p
                JOIN post_keywords pk ON p.id = pk.post_id
                JOIN keywords k ON pk.keyword_id = k.id
                WHERE k.word != %s
                GROUP BY p.id, p.text, p.timestamp
                ORDER BY p.timestamp DESC
                """,
                ("停更",)
            )
            results = cur.fetchall()
            
            ids        = [post[0] for post in results]
            contents   = [post[1] for post in results]
            timestamps = [post[2] for post in results]
            permalinks = [post[3] for post in results]
            
            posts = {}
            for _, id in enumerate(ids):
                posts.update({
                    id: {
                        "content": contents[_],
                        "timestamp": timestamps[_],
                        "permalink": permalinks[_],
                    }
                })
    
    return posts



def get_replies(id: str):
    """
    Fetching replies under the given post
    
    Parameters
    ----------
    id: str
        post id
    
    Returns
    -------
    replies: dict
        a dictionary containing post id and list of replies
        
    """
    with get_vdb_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT text, timestamp FROM replies
                WHERE root_post_id = %s
                ORDER BY timestamp ASC
                """,
                (id,)
            )
            reply_text = [r[0] for r in cur.fetchall()]
            replies = {id: reply_text}
    
    return replies



def assemble(post: str, replies: list):
    """
    Assembling post text and reply text in a string.
    Series title will be trimmed.
    
    Parameters
    ----------
    post: str
        content of post
        
    replies: list
        list of replies of the given post
        
    Returns
    -------
    embed_text: str
    
    """
    # Trimming series title
    title_start = 0
    title_end   = post.find("》")
    title       = post[title_start:title_end+1]
    
    # Assembling post body and replies
    embed_text = post[title_end+3:]
    for r in replies:
        embed_text += "\n\n" + r
    
    return embed_text



def embedding(embed_list: list):
    """
    Generating embedding vectors
    
    Parameters
    ----------
    embed_list: list
        list of embedding text
    
    Returns
    -------
    embeddings: np.ndarray
        embedding vector
        
    """
    with genai.Client() as client:
        response = client.models.embed_content(
            model    = EMBEDDING_MODEL,
            contents = embed_list,
            config   = EmbedContentConfig(
                task_type = EMBEDDING_TASK_TYPE,
                output_dimensionality = DIMENSION
            )
        )
        
        embeddings = []
        for emb in response.embeddings:
            emb  = np.asarray(emb.values)
            emb /= np.sqrt(np.sum(np.square(emb)))
            embeddings.append(emb)
        
    return embeddings



def write_embeddings(ids: list, embeddings: list):
    """
    Writing embedding vectors into database
    
    Parameters
    ----------
    ids: list
        list of post id
    
    embeddings: list
        list of embedding text
        
    Returns
    -------
    None
    
    """
    with get_vdb_connection() as conn:
        with conn.cursor() as cur:
            for id, embedded in zip(ids, embeddings):
                cur.execute(
                    """
                    INSERT INTO items (id, embedding)
                    VALUES (%s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (id, list(embedded))
                )
            conn.commit()
            
    return None

# %% Main
def main():
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
        
    # embedding
    embeddings = embedding(embed_list)
    
    # writing to database
    write_embeddings(posts.keys(), embeddings)
    
    
if __name__ == "__main__":
    main()