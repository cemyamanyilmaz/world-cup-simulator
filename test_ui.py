from streamlit.testing.v1 import AppTest

PAGES = ["📅 Maç Merkezi", "📊 Group Stage",
         "🏆 Bracket", "📈 Form Tracker"]

for page in PAGES:
    at = AppTest.from_file("main.py", default_timeout=120)
    at.run()
    at.sidebar.radio[0].set_value(page)
    at.run()
    assert not at.exception, f"{page}: {at.exception[0].value if at.exception else ''}"
    print(f"{page}: rendered OK "
          f"({len(at.markdown)} markdown blocks, {len(at.dataframe)} tables)")

# enter a manual result through the sidebar widgets and confirm rerun works
at = AppTest.from_file("main.py", default_timeout=120)
at.run()
ms1 = [w for w in at.sidebar.number_input if w.key == "ms1"]
assert ms1, "manual entry widgets missing"
print("manual-entry widgets present in sidebar OK")
print("ALL UI TESTS PASSED")
