class ChunkingException(Exception):
    """Custom exception for errors during text chunking operations."""
    def __init__(self, message: str):
        super().__init__(message)