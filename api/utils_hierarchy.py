from collections import deque
from .models import Category


def get_or_create_category_by_path(path_names):
    """Create (if needed) and return the deepest Category for a list of names.
    Example: ["All Products", "Bakery", "Bread"].
    """
    parent = None
    current = None
    for name in path_names:
        current, _ = Category.objects.get_or_create(name=name, parent=parent)
        parent = current
    return current


def get_descendant_ids(root_id):
    """Return a set of all descendant category IDs including the root."""
    ids = set()
    q = deque([root_id])
    while q:
        cid = q.popleft()
        ids.add(cid)
        for child in Category.objects.filter(parent_id=cid).values_list("id", flat=True):
            if child not in ids:
                q.append(child)
    return ids