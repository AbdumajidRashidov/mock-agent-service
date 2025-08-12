from typing import List, TypedDict

class AbusedRequirement(TypedDict):
    abusedRequirement: str
    reason: str

class RequirementsCheckerResponse(TypedDict):
    abusedRequirements: List[AbusedRequirement]
