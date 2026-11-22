from app.services.analysis_service import analyze_translation


def test_structural_and_content_preservation_perfect():
    py_code = """
def calculate_area(width, height):
    # Calculate geometric area
    message = "calculating..."
    return width * height
"""
    js_code = """
function calculateArea(width, height) {
    // Calculate geometric area
    const message = "calculating...";
    return width * height;
}
"""
    analysis = analyze_translation(py_code, js_code, "python", "javascript")

    metrics = analysis["metrics"]
    assert metrics["structural_preservation"]["score"] == 100
    assert metrics["content_preservation"]["score"] >= 80
    assert metrics["behavioral_verification"]["verified"] is False
    assert metrics["behavioral_verification"]["label"] == "Not verified"

    # Know how transparent disclosures
    know_how = analysis["know_how"]
    assert "Functions: 1 -> 1" in know_how["structural_explanation"]
    assert len(know_how["what_was_not_verified"]) > 0


def test_structural_preservation_divergent():
    py_code = """
def a():
    pass

def b():
    pass
"""
    js_code = """
const x = 42;
"""
    analysis = analyze_translation(py_code, js_code, "python", "javascript")
    metrics = analysis["metrics"]
    # 2 functions in source vs 0 in target
    assert metrics["structural_preservation"]["score"] < 50
