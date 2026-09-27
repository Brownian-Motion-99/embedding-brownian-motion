# %% Packages
import os
import psycopg

# %% Global Variables
from dotenv import load_dotenv
load_dotenv()

# %% Functions

def get_db_connection():
    """
    Getting a connection to threads_backup database.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    conn: psycopg.connect object
    
    """
    conn = psycopg.connect(
        host     = os.environ["DB_BACKUP_HOST"],
        port     = os.environ["DB_BACKUP_PORT"],
        dbname   = os.environ["DB_BACKUP_NAME"],
        user     = os.environ["DB_BACKUP_USER"],
        password = os.environ["DB_BACKUP_PASSWORD"],
    )
    return conn



def get_vdb_connection():
    """
    Getting a connection to threads_vector database.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    conn: psycopg.connect object
    
    """
    conn = psycopg.connect(
        host     = os.environ["DB_VECTOR_HOST"],
        port     = os.environ["DB_VECTOR_PORT"],
        dbname   = os.environ["DB_VECTOR_NAME"],
        user     = os.environ["DB_VECTOR_USER"],
        password = os.environ["DB_VECTOR_PASSWORD"],
    )
    return conn