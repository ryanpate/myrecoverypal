"""All-caps feed names are shown in normal case; hub pages carry H2s."""
from datetime import time

from django.test import SimpleTestCase, TestCase, override_settings

from apps.support_services.models import Meeting, readable_name


class ReadableNameTests(SimpleTestCase):

    def test_all_caps_name_becomes_normal_case(self):
        self.assertEqual(readable_name('SAT MENS EARLY AWAKENING'), 'Sat Mens Early Awakening')

    def test_program_acronyms_stay_upper(self):
        self.assertEqual(readable_name('NA BEGINNERS (STEP STUDY)'), 'NA Beginners (Step Study)')
        self.assertEqual(readable_name('LGBTQ+ AA OF THE VALLEY'), 'LGBTQ+ AA of the Valley')

    def test_apostrophes_and_hyphens(self):
        self.assertEqual(readable_name("MEN'S 12-STEP GROUP"), "Men's 12-Step Group")

    def test_first_word_is_capitalised_even_if_small(self):
        self.assertEqual(readable_name('A NEW BEGINNING'), 'A New Beginning')

    def test_mixed_case_names_are_left_alone(self):
        self.assertEqual(readable_name('Grateful Hearts of NYC'), 'Grateful Hearts of NYC')
        self.assertEqual(readable_name('7 AM'), '7 AM')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ReadableNameOnPagesTests(TestCase):
    def setUp(self):
        for i in range(3):
            Meeting.objects.create(
                name=f'EARLY BIRDS {i}', slug=f'early-{i}', day=i, time=time(7, 0),
                attendance_option='in_person', location='Hall', city='Houston', state='TX',
                is_approved=True, is_active=True)

    def test_detail_title_h1_and_schema_use_normal_case(self):
        html = self.client.get('/support/meetings/early-0/').content.decode()
        self.assertIn('<title>Early Birds 0', html)
        self.assertIn('<h1 class="meeting-detail-name">Early Birds 0</h1>', html)
        self.assertIn('"name": "Early Birds 0"', html)
        self.assertNotIn('EARLY BIRDS', html)

    def test_city_hub_lists_normal_case_names(self):
        html = self.client.get('/support/meetings/tx/houston/').content.decode()
        self.assertIn('<strong>Early Birds 1</strong>', html)

    def test_state_hub_and_finder_have_h2s(self):
        self.assertIn('<h2', self.client.get('/support/meetings/tx/').content.decode())
        self.assertIn('<h2', self.client.get('/support/meetings/').content.decode())
