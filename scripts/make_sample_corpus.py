"""Create a small synthetic corpus of Hebrew protocols in data/raw/.

All content is invented. Half of the files are stored in visual order (like many
government PDFs) so the Hebrew fixer is exercised.
Usage:  python -m scripts.make_sample_corpus
"""

from pathlib import Path

from bidi import get_display
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from scripts.fonts import find_hebrew_font

OUT_DIR = Path("data/raw")

# filename -> (visual_order, [page, ...]) where page is a list of lines
CORPUS = {
    "hygiene_hands.pdf": (
        False,
        [
            [
                "נוהל היגיינת ידיים מספר 03/2024",
                "מטרת הנוהל היא להפחית זיהומים הקשורים לטיפול רפואי.",
                "יש לבצע היגיינת ידיים בחמישה רגעים: לפני מגע במטופל,",
                "לפני פעולה אספטית, לאחר חשיפה לנוזלי גוף,",
                "לאחר מגע במטופל ולאחר מגע בסביבתו.",
            ],
            [
                "שטיפה במים וסבון תימשך בין 40 ל-60 שניות.",
                "חיטוי בג'ל אלכוהולי יימשך בין 20 ל-30 שניות עד להתייבשות.",
                "כאשר הידיים מזוהמות באופן נראה לעין יש לשטוף במים וסבון.",
                "אין לענוד תכשיטים על כפות הידיים ועל פרקי הידיים בזמן טיפול.",
            ],
        ],
    ),
    "high_risk_medication.pdf": (
        False,
        [
            [
                "נוהל מתן תרופות בסיכון גבוה מספר 07/2024",
                "תרופות בסיכון גבוה כוללות אינסולין, הפרין ואשלגן כלורי.",
                "מתן תרופה כזו מחייב בדיקה כפולה על ידי שתי אחיות.",
                "האחות השנייה תאמת את שם התרופה, המינון והדרך למתן.",
            ],
            [
                "אשלגן כלורי מרוכז לא יאוחסן במחלקות הרגילות.",
                "מינון אינסולין יירשם ביחידות ולא בקיצור.",
                "כל טעות או כמעט-טעות במתן תרופה תדווח תוך 24 שעות.",
            ],
        ],
    ),
    "fall_prevention.pdf": (
        True,
        [
            [
                "נוהל מניעת נפילות מספר 11/2023",
                "כל מטופל יעבור הערכת סיכון לנפילה תוך 24 שעות מקבלתו.",
                "ההערכה תתבצע באמצעות סולם מורס.",
                "ציון 45 ומעלה מצביע על סיכון גבוה לנפילה.",
            ],
            [
                "למטופל בסיכון גבוה יוצמד שלט אזהרה בצבע צהוב.",
                "מיטת המטופל תונמך ותצויד במעקות צד על פי הצורך.",
                "הערכה חוזרת תתבצע בכל שינוי במצב הקליני של המטופל.",
            ],
        ],
    ),
    "patient_admission.pdf": (
        False,
        [
            [
                "נוהל קבלת מטופל למחלקה מספר 02/2024",
                "זיהוי המטופל יתבצע באמצעות שני מזהים: שם מלא ומספר תעודת זהות.",
                "אחות תקבל את המטופל ותבצע סקירה ראשונית תוך 30 דקות.",
            ],
            [
                "יש לבדוק רגישויות ואלרגיות ולתעד אותן בתיק הרפואי.",
                "צמיד זיהוי יוצמד לפרק היד של המטופל בעת הקבלה.",
                "משפחת המטופל תקבל הסבר על נהלי המחלקה ושעות הביקור.",
            ],
        ],
    ),
    "safety_incident.pdf": (
        True,
        [
            [
                "נוהל דיווח על אירוע בטיחות מספר 12/2024",
                "כל עובד שזיהה אירוע חריג ידווח למנהל המחלקה תוך 24 שעות.",
                "הדיווח יתבצע בטופס המקוון במערכת EMR של בית החולים.",
            ],
            [
                "מנהל המחלקה יעביר את הדיווח לוועדת הבטיחות בתוך שלושה ימים.",
                "יש לתעד את מיקום האירוע והצעדים שננקטו מיד.",
                "הדיווח נועד ללמידה ולא להענשת עובדים.",
            ],
        ],
    ),
}


def make_pdf(path: Path, pages: list[list[str]], visual: bool) -> None:
    font = find_hebrew_font()
    if not font:
        raise SystemExit("No Hebrew-capable TTF font found (see scripts/fonts.py)")
    pdfmetrics.registerFont(TTFont("HebFont", font))
    c = canvas.Canvas(str(path))
    for lines in pages:
        c.setFont("HebFont", 12)
        y = 800
        for line in lines:
            c.drawRightString(555, y, get_display(line) if visual else line)
            y -= 24
        c.showPage()
    c.save()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, (visual, pages) in CORPUS.items():
        make_pdf(OUT_DIR / name, pages, visual)
        print(f"Created {OUT_DIR / name} ({'visual' if visual else 'logical'} order)")


if __name__ == "__main__":
    main()
