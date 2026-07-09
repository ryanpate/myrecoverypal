# apps/accounts/court_models.py
"""
Court Compliance models — attendance tracking and tamper-evident reports
for court-ordered AA/NA/SMART meeting attendees.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


PROGRAM_CHOICES = [
    ('aa', 'Alcoholics Anonymous'),
    ('na', 'Narcotics Anonymous'),
    ('ca', 'Cocaine Anonymous'),
    ('ma', 'Marijuana Anonymous'),
    ('ga', 'Gamblers Anonymous'),
    ('smart', 'SMART Recovery'),
    ('refuge', 'Refuge Recovery'),
    ('lifering', 'LifeRing'),
    ('other', 'Other Recovery Program'),
]

MEETING_TYPE_CHOICES = [
    ('open', 'Open'),
    ('closed', 'Closed'),
    ('discussion', 'Discussion'),
    ('speaker', 'Speaker'),
    ('step', 'Step Study'),
    ('big_book', 'Big Book Study'),
    ('beginners', 'Beginners / Newcomers'),
    ('mens', "Men's"),
    ('womens', "Women's"),
    ('lgbtq', 'LGBTQ+'),
    ('other', 'Other'),
]

VERIFICATION_CHOICES = [
    ('self', 'Self-Reported'),
    ('signature', 'Digital Chair Signature'),
    ('photo', 'Photo of Attendance Card'),
    ('gps', 'GPS Verified'),
    ('qr', 'QR Code Check-In'),
]


class CourtReportProfile(models.Model):
    """Stable court-ordered context for a user — case number, PO contact, etc."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='court_profile',
    )

    # Legal identity (separate from username, only used on court reports)
    legal_name = models.CharField(max_length=200, blank=True)

    # Court context
    case_number = models.CharField(max_length=80, blank=True)
    court_name = models.CharField(max_length=200, blank=True)
    jurisdiction = models.CharField(max_length=120, blank=True, help_text='State, county, or city')
    judge_name = models.CharField(max_length=120, blank=True)

    # Probation / referral contact
    probation_officer_name = models.CharField(max_length=120, blank=True)
    probation_officer_email = models.EmailField(blank=True)
    attorney_email = models.EmailField(blank=True)

    # Compliance requirements
    required_meetings_per_week = models.PositiveIntegerField(default=3)
    report_period_start = models.DateField(
        null=True, blank=True,
        help_text='Start date the user is required to track from (e.g. sentencing date).',
    )
    report_period_end = models.DateField(
        null=True, blank=True,
        help_text='End date of compliance requirement (e.g. next court date or probation end).',
    )

    # Behavior
    auto_email_monthly = models.BooleanField(
        default=False,
        verbose_name='Auto-email monthly report to my probation officer',
        help_text="On the 1st of each month, automatically generate last month's "
                  "attendance report and email it to your probation officer.",
    )

    # Task dedupe stamps (user-local dates)
    last_meeting_reminder_sent = models.DateField(null=True, blank=True)
    last_auto_po_email_sent = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'court_report_profiles'
        verbose_name = 'Court Report Profile'
        verbose_name_plural = 'Court Report Profiles'

    def __str__(self):
        return f"{self.user.username} — court profile (case {self.case_number or 'none'})"

    def save(self, *args, **kwargs):
        if not self.report_period_start:
            self.report_period_start = timezone.now().date()
        super().save(*args, **kwargs)


class MeetingAttendance(models.Model):
    """One attended recovery meeting. Drives the court report."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meeting_attendances',
    )

    # Optional link to a Meeting row from the existing meeting finder
    meeting = models.ForeignKey(
        'support_services.Meeting',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='attendances',
    )

    # Free-text fallbacks (always required so reports work without a Meeting row)
    meeting_name = models.CharField(max_length=200)
    meeting_date = models.DateTimeField()
    meeting_end_time = models.DateTimeField(null=True, blank=True)
    meeting_address = models.CharField(max_length=300, blank=True)
    meeting_online = models.BooleanField(default=False)
    meeting_platform = models.CharField(
        max_length=80, blank=True,
        help_text='Zoom, online group AA, etc. — only when meeting_online=True.',
    )

    program = models.CharField(max_length=20, choices=PROGRAM_CHOICES, default='aa')
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPE_CHOICES, default='open')

    verification_method = models.CharField(
        max_length=20, choices=VERIFICATION_CHOICES, default='self',
    )

    # Phase 1: digital chair signature is just a typed name + timestamp.
    # Phase 2 will add per-signer verification.
    chair_signature_name = models.CharField(max_length=120, blank=True)
    chair_signature_at = models.DateTimeField(null=True, blank=True)

    # Phase 2 fields (declared now so migrations don't churn later)
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    attendance_photo = models.ImageField(upload_to='court/attendance/', null=True, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'meeting_attendances'
        verbose_name = 'Meeting Attendance'
        verbose_name_plural = 'Meeting Attendances'
        ordering = ['-meeting_date']
        indexes = [
            models.Index(fields=['user', '-meeting_date']),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.meeting_name} on {self.meeting_date:%Y-%m-%d}"


class CourtReport(models.Model):
    """A generated PDF report covering a period — immutable once created."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='court_reports',
    )

    period_start = models.DateField()
    period_end = models.DateField()

    # Legacy external-storage field. New reports store bytes in pdf_data —
    # court documents are small (~26KB), privacy-sensitive, and Cloudinary
    # refuses PDF delivery (401), so Postgres is the canonical home.
    pdf = models.FileField(upload_to='court/reports/', null=True, blank=True)
    pdf_data = models.BinaryField(null=True, blank=True, editable=False,
                                  help_text='PDF bytes (canonical storage)')
    pdf_hash = models.CharField(max_length=64, db_index=True, help_text='SHA-256 of the PDF bytes')
    # The fingerprint PRINTED INSIDE the PDF. Necessarily different from
    # pdf_hash — a hash embedded in the bytes cannot also be the hash of those
    # bytes. The verify endpoint accepts either, so a PO can verify from the
    # printed page (embedded hash) or from the file itself (pdf_hash).
    pdf_embedded_hash = models.CharField(
        max_length=64, db_index=True, blank=True, default='',
        help_text='SHA-256 fingerprint printed inside the PDF')
    attendance_count = models.PositiveIntegerField(default=0)

    # Snapshot of profile fields at the moment of generation (so a report
    # remains accurate even if the user later changes their case number).
    legal_name_snapshot = models.CharField(max_length=200, blank=True)
    case_number_snapshot = models.CharField(max_length=80, blank=True)
    court_name_snapshot = models.CharField(max_length=200, blank=True)

    # Email audit trail
    emailed_to = models.TextField(blank=True, help_text='Comma-separated recipients')
    emailed_at = models.DateTimeField(null=True, blank=True)

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'court_reports'
        verbose_name = 'Court Report'
        verbose_name_plural = 'Court Reports'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['user', '-generated_at']),
            models.Index(fields=['pdf_hash']),
        ]

    def __str__(self):
        return f"{self.user.username} — court report {self.period_start:%Y-%m} to {self.period_end:%Y-%m}"

    @property
    def short_hash(self):
        return self.pdf_hash[:8] if self.pdf_hash else ''

    def get_pdf_bytes(self):
        """Return the PDF bytes, or None if unavailable.

        Postgres (pdf_data) is canonical; the legacy FileField is a fallback
        for rows created before 2026-07 (its storage may refuse reads)."""
        if self.pdf_data:
            return bytes(self.pdf_data)
        if self.pdf:
            try:
                data = self.pdf.read()
                self.pdf.close()
                return data
            except Exception:
                return None
        return None
