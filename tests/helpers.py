def make_record(**overrides):
    payload = {
        "record_id": "R-1001",
        "patient_id": "P-1001",
        "patient_name": "Test Patient Alice",
        "date_of_birth": "1958-04-12",
        "ssn_last4": "1234",
        "contact_phone": "555-0001",
        "facility": "Lakeview Main",
        "timestamp": "2024-04-01T14:22:00Z",
        "event_type": "REGISTRATION",
        "diagnosis_codes": [],
    }
    payload.update(overrides)
    return payload
