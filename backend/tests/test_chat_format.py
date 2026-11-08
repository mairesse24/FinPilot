from app.services.chat_format import FINANCIAL_NUMBER, format_reply


def test_risk_and_action_are_separate_without_changing_financial_values():
    fact = ("Guardian (medium priority, 30-day outlook): Low balance. "
            "Checking holds $2,400.00 and could dip to $365.08. "
            "Action to explore: Test a $150.00 spending cut over 10 days.")
    reply = format_reply([("Risk", fact)], "Would you like to test that scenario?", "Prototype estimate.")
    assert reply.startswith("### Risk\n\n- Guardian")
    risk, action = reply.split("### Actions to explore")
    assert "$150.00" not in risk and "**$150.00**" in action
    assert "- Checking holds **$2,400.00** and could dip to **$365.08**." in risk
    assert FINANCIAL_NUMBER.findall(reply.replace("**", "")) == FINANCIAL_NUMBER.findall(fact)
    assert "\n\nWould you like to test that scenario?\n\nPrototype estimate." in reply


def test_scores_and_percentages_are_bold_without_splitting_decimals():
    fact = "Your financial health score is 62.4 out of 100. Spending discipline: 13/100. Debt is 1%."
    reply = format_reply([("Health score", fact)], "", "Prototype estimate.")
    assert "**62.4** out of 100" in reply
    assert "**13/100**" in reply and "**1%**" in reply
    assert "62.\n" not in reply
    assert FINANCIAL_NUMBER.findall(reply.replace("**", "")) == FINANCIAL_NUMBER.findall(fact)


def test_sections_are_selected_by_tool_evidence_not_model_authored_labels():
    reply = format_reply([
        ("Scenario comparison", "Baseline $365.08. Scenario $565.08."),
        ("Forecast", "The 30-day forecast uses a $500.00 buffer."),
    ], "Explore another horizon?", "Prototype estimate.")
    assert "### Scenario comparison" in reply and "### Forecast" in reply
    assert "### Actions to explore" in reply
    assert "$999" not in reply
