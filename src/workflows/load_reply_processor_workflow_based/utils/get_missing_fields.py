from typing import Any, List

def get_missing_fields(load: Any) -> List[str]:
    """Get a list of missing required fields from the load.

    Args:
        load (Any): The load object containing email history and equipment details

    Returns:
        List[str]: List of missing field names
    """
    fields = []

    if not load.get('emailHistory', {}).get('details', {}).get('commodity'):
        fields.append('commodity')

    if not load.get('emailHistory', {}).get('details', {}).get('weight'):
        fields.append('weight')

    if not load.get('equipmentType'):
        fields.append('equipmentType')

    if not load.get('emailHistory', {}).get('details', {}).get('deliveryDateTime'):
        fields.append('deliveryDate')

    return fields
