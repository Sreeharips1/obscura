from app.privacy.detectors.pii_model import detect_pii


text = """
My name is Sreehari. Sreehari wish to join consyst pvt
and moved to Kochi. My email is sreehari@gmail.com
and my phone number is 9864363787.
"""


print("\n========== GLINER PII TEST ==========\n")


detections = detect_pii(text)


for detection in detections:

    print(
        f"{detection.type:20} | "
        f"{detection.value:30} | "
        f"{detection.confidence:.2f} | "
        f"{detection.risk}"
    )


print(
    "\n=====================================\n"
)