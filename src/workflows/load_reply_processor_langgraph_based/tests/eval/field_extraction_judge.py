from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class FieldExtractionResult(BaseModel):
    """Result of field extraction comparison by AI judge."""
    accuracy_score: int = Field(..., description="Score 1-10 for field extraction accuracy")
    semantic_score: int = Field(..., description="Score 1-10 for semantic equivalence")
    completeness_score: int = Field(..., description="Score 1-10 for completeness of extraction")
    overall_score: int = Field(..., description="Overall score 1-10")
    passes: bool = Field(..., description="Whether field extraction passes evaluation")
    feedback: str = Field(..., description="Detailed feedback on the comparison")
    field_analysis: Optional[Dict[str, str]] = Field(default=None, description="Per-field analysis")

FIELD_EXTRACTION_JUDGE_PROMPT = """
You are an expert evaluator for trucking industry data extraction. Compare EXPECTED field extractions with ACTUAL field extractions from an AI system.

EVALUATION CRITERIA:

1. ACCURACY (1-10):
   - Are the extracted values factually correct?
   - Do numeric values match (allowing for reasonable format differences)?
   - Are rates, weights, dates correctly identified?

2. SEMANTIC EQUIVALENCE (1-10):
   - Do extracted values have the same meaning even if worded differently?
   - Examples: "auto parts" vs "automotive parts" = equivalent
   - "electronics" vs "electronic equipment" = equivalent
   - "7/15 2pm" vs "7/15 at 2:00 PM" = equivalent

3. COMPLETENESS (1-10):
   - Are all expected fields extracted?
   - Are there significant missing extractions?
   - Are there unexpected but valuable extractions?

FIELD-SPECIFIC RULES:

**Rates (rateInfo.rateUsd):**
- 1800 vs "1800" vs "$1800" = equivalent
- Multiple rates: should extract highest unless specified otherwise

**Weights:**
- 35000 vs "35k" vs "35,000" = equivalent
- Convert kg to lbs: 1000kg = 2204.62 lbs

**Commodities:**
- "electronics" vs "electronic parts" vs "electronic equipment" = similar
- "auto parts" vs "automotive parts" vs "car parts" = similar

**Dates/Times:**
- "7/15 2pm" vs "7/15 at 2:00 PM" vs "July 15 at 2pm" = equivalent
- "PU 6/20 8am" vs "pickup 6/20 at 8am" = equivalent

**Dimensions:**
- Allow reasonable unit conversions (ft to inches, cm to inches)
- 48ft = 576 inches, 8ft = 96 inches

**Special Notes:**
- Focus on CRITICAL requirements only (hazmat, temperature, permits)
- Ignore non-critical details (pallet counts, standard loading)

SCORING GUIDELINES:
- 9-10: Perfect or semantically equivalent extractions
- 7-8: Good extractions with minor format differences
- 5-6: Mostly correct but some missing or incorrect fields
- 3-4: Several errors or missing critical information
- 1-2: Major extraction failures

PASS THRESHOLD: Overall score >= 7

Be lenient with format differences but strict with factual accuracy. Focus on whether a human dispatcher would consider the extractions equivalent and usable.
"""

class FieldExtractionJudge:
    """AI-powered field extraction comparison judge."""

    def __init__(self):
        self.llm = init_chat_model(
            "azure_openai:gpt-4o",
            temperature=0.3,  # Lower temperature for consistent evaluation
        ).with_structured_output(FieldExtractionResult, method="function_calling")

    def compare_field_extractions(self, expected: Dict[str, Any], actual: Dict[str, Any], context: Dict[str, Any] = None) -> FieldExtractionResult:
        """
        Compare expected vs actual field extractions using AI judge.

        Args:
            expected: Expected field extractions
            actual: Actual extracted fields
            context: Additional context about the test case

        Returns:
            FieldExtractionResult with scores and feedback
        """
        expected_fields = expected.get('field_updates', {})
        actual_fields = actual.get('field_updates', {})

        # If no fields to compare, return perfect score
        if not expected_fields and not actual_fields:
            return FieldExtractionResult(
                accuracy_score=10,
                semantic_score=10,
                completeness_score=10,
                overall_score=10,
                passes=True,
                feedback="No field extractions to compare - both empty",
                field_analysis={}
            )

        context_info = ""
        if context:
            context_info = f"TEST CONTEXT: {context.get('description', '')}\nCATEGORY: {context.get('category', '')}\n\n"

        # Format field comparison for the prompt
        comparison_text = f"""
{context_info}EXPECTED FIELD EXTRACTIONS:
{self._format_fields(expected_fields)}

ACTUAL FIELD EXTRACTIONS:
{self._format_fields(actual_fields)}

Evaluate the accuracy and semantic equivalence of the field extractions."""

        try:
            result = self.llm.invoke([
                SystemMessage(content=FIELD_EXTRACTION_JUDGE_PROMPT),
                HumanMessage(content=comparison_text)
            ])
            return result
        except Exception as e:
            # Fallback evaluation if LLM fails
            return FieldExtractionResult(
                accuracy_score=1,
                semantic_score=1,
                completeness_score=1,
                overall_score=1,
                passes=False,
                feedback=f"Error during evaluation: {str(e)}",
                field_analysis={}
            )

    def _format_fields(self, fields: Dict[str, Any]) -> str:
        """Format fields dictionary for display in prompt."""
        if not fields:
            return "No fields extracted"

        formatted = []
        for field, value in fields.items():
            formatted.append(f"  {field}: {value}")

        return "\n".join(formatted)
