from pydantic import BaseModel, Field

class AnalysisResponse(BaseModel):
    executive_summary: str = Field(description="A direct answer in two to four sentences.")
    market_data: list[str] = Field(default_factory=list, description="Verified market observations with evidence IDs.")
    news_context: list[str] = Field(default_factory=list, description="Verified news observations with evidence IDs.")
    ai_analysis: list[str] = Field(default_factory=list, description="Evidence-grounded interpretations, not hidden reasoning.")
    risks: list[str] = Field(default_factory=list, description="Risks, uncertainty, or missing-data notes.")
    sources: list[str] = Field(default_factory=list, description="Evidence IDs and URLs only when supplied.")

    def to_markdown(self) -> str:
        def section(title: str, values: list[str]) -> str:
            return f"### {title}\n" + ("\n".join(f"- {v}" for v in values) if values else "- No verified information available.")
        return "\n\n".join([
            "## Executive Summary\n" + self.executive_summary,
            section("Market Data", self.market_data),
            section("News & Context", self.news_context),
            section("AI Analysis", self.ai_analysis),
            section("Risks & Uncertainty", self.risks),
            section("Sources", self.sources),
        ])
