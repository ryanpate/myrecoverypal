"""Draft new written resources to fill the previously-empty resource categories.

Each resource is a free, static article with real on-page HTML content and an
SEO meta description, so every page is genuinely useful and worth indexing.
Idempotent: categories use get_or_create, resources use update_or_create by
slug. Safe to run on production after deploy:

    python manage.py populate_category_resources
"""
from django.core.management.base import BaseCommand

from resources.models import Resource, ResourceCategory, ResourceType


# Categories that should exist (matches populate_resources.py definitions).
CATEGORIES = [
    ('educational', 'Educational Materials', '📚',
     'Learn about addiction, recovery processes, and evidence-based treatment approaches', 1),
    ('support', 'Support Services', '🤝',
     'Find support groups, helplines, and community resources near you', 2),
    ('wellness', 'Wellness Resources', '🧘',
     'Mindfulness, meditation, and holistic health resources', 4),
    ('family', 'Family & Friends', '👨‍👩‍👧‍👦',
     'Resources for loved ones supporting someone in recovery', 5),
    ('professional', 'Professional Help', '⚕️',
     'Find treatment centers, therapists, and medical professionals', 6),
]

SAFETY = ('<p><em>This article is educational and is not a substitute for '
          'professional medical advice, diagnosis, or treatment. If you are in '
          'crisis, call or text 988 (Suicide &amp; Crisis Lifeline).</em></p>')

# category_slug, title, slug, description, meta_description, content(HTML)
RESOURCES = [
    # ---- Educational Materials ----
    ('educational',
     'The Stages of Change in Recovery',
     'stages-of-change-recovery',
     'Understand the five stages of change and where you are in your recovery journey.',
     'The five stages of change in addiction recovery explained: precontemplation, '
     'contemplation, preparation, action, and maintenance. Learn where you are and '
     'what helps at each step.',
     """
<h2>Recovery happens in stages, not all at once</h2>
<p>Change is a process, not a single decision. The widely used
<strong>Stages of Change</strong> model (the transtheoretical model) describes
five steps people move through when they change a behavior like substance use.
Knowing which stage you're in helps you set realistic expectations and pick the
right next step &mdash; instead of judging yourself for not being further along.</p>

<h2>The five stages</h2>
<h3>1. Precontemplation</h3>
<p>Not yet considering change, often unaware there's a problem or feeling
defensive about it. What helps: honest information and people who plant seeds
without pushing.</p>
<h3>2. Contemplation</h3>
<p>Aware of the problem and weighing the pros and cons. Ambivalence is normal
here &mdash; wanting to change and not wanting to, at the same time. What helps:
listing your reasons and imagining life on the other side.</p>
<h3>3. Preparation</h3>
<p>Decided to change and starting to plan &mdash; setting a quit date, telling
someone, looking into support. What helps: a concrete plan and a support system
lined up before you start.</p>
<h3>4. Action</h3>
<p>Actively changing your behavior and building new routines. This stage takes
real energy. What helps: daily structure, coping skills, and removing triggers.</p>
<h3>5. Maintenance</h3>
<p>Sustaining the change over months and years and guarding against relapse. What
helps: community, ongoing check-ins, and a relapse-prevention plan.</p>

<h2>Relapse is a step, not the end</h2>
<p>Many people cycle through these stages more than once. A return to use isn't
failure &mdash; it's information. Most people who reach lasting recovery moved
through the stages several times first. Wherever you are right now is a valid
place to start.</p>
""" + SAFETY),

    ('educational',
     'What Is Post-Acute Withdrawal Syndrome (PAWS)?',
     'post-acute-withdrawal-syndrome-paws',
     'Learn what PAWS is, the symptoms to expect, and how to get through it.',
     'Post-acute withdrawal syndrome (PAWS) explained: common symptoms like mood '
     'swings, brain fog, and sleep problems, how long it lasts, and practical ways '
     'to cope in early recovery.',
     """
<h2>Why you can still feel off weeks after quitting</h2>
<p>Acute withdrawal &mdash; the intense physical symptoms in the first days after
stopping &mdash; usually fades within a week or two. But many people then notice a
second, longer wave of symptoms that come and go for months. This is
<strong>post-acute withdrawal syndrome (PAWS)</strong>, and it happens as your
brain slowly rebalances its chemistry after substance use. Knowing it's normal
&mdash; and temporary &mdash; makes it far easier to ride out.</p>

<h2>Common symptoms</h2>
<ul>
  <li>Mood swings, irritability, anxiety, or low mood</li>
  <li>Trouble sleeping or vivid dreams</li>
  <li>Brain fog, poor concentration, and memory lapses</li>
  <li>Low energy and trouble feeling pleasure (anhedonia)</li>
  <li>Heightened sensitivity to stress</li>
  <li>Cravings that surface unexpectedly</li>
</ul>
<p>PAWS tends to come in waves rather than staying constant. A hard day or two
can be followed by a stretch of feeling fine. Over time the good stretches get
longer and the symptoms get milder.</p>

<h2>How long does it last?</h2>
<p>It varies by person and substance, but symptoms commonly ebb and flow for
several months and gradually lift over the first year or two of recovery. The
trajectory is uneven but the overall direction is up.</p>

<h2>What actually helps</h2>
<ul>
  <li><strong>Protect your sleep</strong> &mdash; consistent bedtimes and a wind-down routine.</li>
  <li><strong>Move your body</strong> &mdash; even short walks help mood and brain recovery.</li>
  <li><strong>Eat and hydrate regularly</strong> &mdash; stable blood sugar steadies mood.</li>
  <li><strong>Name it when it hits</strong> &mdash; &ldquo;this is PAWS, not the real me, and it passes.&rdquo;</li>
  <li><strong>Stay connected</strong> &mdash; tell someone when you're in a wave.</li>
</ul>
<p>If symptoms are severe or you're having thoughts of self-harm, reach out to a
healthcare professional &mdash; PAWS is manageable, and you don't have to white-
knuckle it alone.</p>
""" + SAFETY),

    # ---- Support Services ----
    ('support',
     'How to Find a Recovery Support Group That Fits',
     'find-recovery-support-group',
     'A program-neutral guide to the main types of recovery groups and how to choose.',
     'Compare the main recovery support groups: AA, NA, SMART Recovery, Refuge '
     'Recovery, LifeRing, and Women for Sobriety. A program-neutral guide to finding '
     'the meeting that fits you.',
     """
<h2>There's no single &ldquo;right&rdquo; program</h2>
<p>Connection is one of the strongest protectors in recovery, and support groups
are one of the easiest ways to find it. But people are different, and so are
groups. The best program is the one you'll actually keep going back to. Here's a
program-neutral look at the main options so you can find your fit.</p>

<h2>The main types of groups</h2>
<ul>
  <li><strong>12-Step (AA, NA, CA, GA, etc.):</strong> the most widely available,
  free, peer-led, spiritually framed, and built around sponsorship and the
  twelve steps. Meetings almost everywhere, in person and online.</li>
  <li><strong>SMART Recovery:</strong> secular and science-based, using
  cognitive-behavioral tools and a self-empowerment approach rather than steps or
  a higher power.</li>
  <li><strong>Refuge Recovery / Recovery Dharma:</strong> Buddhist-inspired,
  using mindfulness and meditation as the path.</li>
  <li><strong>LifeRing:</strong> secular, abstinence-based, focused on your own
  &ldquo;sober self&rdquo; rather than a set program.</li>
  <li><strong>Women for Sobriety:</strong> designed around the specific needs and
  experiences of women in recovery.</li>
</ul>

<h2>How to choose</h2>
<ol>
  <li><strong>Try several.</strong> Visit a few different groups &mdash; and a few
  different meetings within the same program, since each has its own personality.</li>
  <li><strong>Notice how you feel after.</strong> A good fit leaves you feeling a
  little lighter and less alone, even on a hard night.</li>
  <li><strong>Don't judge a program by one meeting.</strong> Give any group a few
  visits before deciding.</li>
  <li><strong>Mix and match.</strong> Many people combine a group with therapy,
  an online community, and their own routines.</li>
</ol>

<h2>Online counts too</h2>
<p>If getting to a meeting is hard, online and text-based communities are real
support. The goal is simply this: don't do recovery alone.</p>
""" + SAFETY),

    ('support',
     'How to Find and Work With a Sponsor',
     'how-to-find-a-sponsor',
     'What a sponsor does, how to ask someone, and how to make the relationship work.',
     'A practical guide to finding a recovery sponsor: what a sponsor is (and isn\'t), '
     'how to ask someone to sponsor you, and how to build a relationship that '
     'supports your sobriety.',
     """
<h2>What a sponsor is &mdash; and isn't</h2>
<p>A sponsor is someone further along in recovery who guides you through a program
and is there for you between meetings. They've walked the road you're on. A
sponsor is <strong>not</strong> a therapist, a sober coach for hire, a bank, or
someone responsible for keeping you sober &mdash; that part is always yours. What
they offer is experience, accountability, and a phone number you can call at 2am.</p>

<h2>How to find one</h2>
<ul>
  <li><strong>Keep showing up.</strong> The simplest way to meet potential sponsors
  is to attend the same meetings regularly and listen for people whose recovery
  you respect.</li>
  <li><strong>Look for someone who has what you want.</strong> Steady time, a life
  you'd like to have, and a way of talking about recovery that resonates.</li>
  <li><strong>Match where it matters.</strong> Many programs suggest a sponsor of
  the same gender, or whoever you're not likely to be attracted to, to keep the
  relationship focused.</li>
</ul>

<h2>How to ask</h2>
<p>It's simpler than it feels. Approach someone after a meeting and say,
&ldquo;Would you be willing to sponsor me, or talk about it?&rdquo; A no usually
just means they're at capacity &mdash; it's not personal, and they'll often point
you to someone else. Asking is a sign of strength, not weakness.</p>

<h2>Making it work</h2>
<ul>
  <li>Agree on how and when you'll stay in touch.</li>
  <li>Be honest &mdash; a sponsor can only help with what you tell them.</li>
  <li>Do the work between conversations.</li>
  <li>If the fit isn't right, it's okay to change sponsors. The relationship
  serves your recovery, not the other way around.</li>
</ul>
<p>A temporary sponsor is a great way to start if you're not ready to commit
&mdash; the important thing is to reach out to someone now rather than waiting for
the perfect match.</p>
""" + SAFETY),

    # ---- Wellness Resources ----
    ('wellness',
     'Mindfulness and Meditation for Early Recovery',
     'mindfulness-meditation-early-recovery',
     'How mindfulness helps with cravings and stress, plus simple ways to start.',
     'How mindfulness and meditation support early recovery: calming cravings with '
     'urge surfing, reducing stress, and simple beginner practices you can start in '
     'five minutes a day.',
     """
<h2>Why mindfulness helps in recovery</h2>
<p>Mindfulness simply means paying attention to the present moment without judging
it. That skill is unexpectedly powerful in recovery, because so much of addiction
runs on autopilot &mdash; a trigger, a craving, a reaction, all before you've
consciously chosen anything. Mindfulness opens a gap between the urge and the
action, and that gap is where recovery lives.</p>

<h2>Riding out cravings with &ldquo;urge surfing&rdquo;</h2>
<p>Cravings rise, peak, and fall like a wave, usually within 15&ndash;30 minutes.
Urge surfing means observing a craving instead of fighting it: notice where you
feel it in your body, rate its intensity, and breathe while you watch it shift.
Treating a craving as a passing sensation rather than a command takes away most of
its power.</p>

<h2>Simple practices to start</h2>
<ul>
  <li><strong>Five-minute breath focus:</strong> sit comfortably, follow your
  breath in and out, and gently return your attention each time it wanders. That
  returning <em>is</em> the practice &mdash; you're not failing when your mind drifts.</li>
  <li><strong>5-4-3-2-1 grounding:</strong> name five things you see, four you can
  touch, three you hear, two you smell, one you taste. Great for anxiety spikes.</li>
  <li><strong>Body scan:</strong> slowly move your attention from head to toe,
  noticing tension without trying to fix it.</li>
  <li><strong>Mindful walking:</strong> a walk where you focus on the feeling of
  each step and the sounds around you.</li>
</ul>

<h2>Make it stick</h2>
<p>Consistency beats length. Five minutes a day does more than an occasional long
session. Guided apps and recordings make starting easier, and tying practice to an
existing habit &mdash; right after your morning coffee, say &mdash; helps it
become routine. Like any skill, it gets easier with repetition.</p>
""" + SAFETY),

    ('wellness',
     'Sleep, Nutrition, and Exercise: Rebuilding Your Body in Recovery',
     'sleep-nutrition-exercise-recovery',
     'How the basics of physical health speed up healing and protect your sobriety.',
     'How sleep, nutrition, and exercise support addiction recovery. Practical, '
     'doable habits to rebuild your body, steady your mood, and lower relapse risk '
     'in early sobriety.',
     """
<h2>Your body is healing &mdash; help it</h2>
<p>Substance use takes a toll on sleep, appetite, and physical health, and those
same systems strongly influence mood and cravings. Tending to the basics isn't
just &ldquo;self-care&rdquo; &mdash; it directly lowers relapse risk. Remember
<strong>HALT</strong>: being Hungry, Angry, Lonely, or Tired makes cravings far
stronger, and three of those four are physical.</p>

<h2>Sleep</h2>
<p>Sleep is often disrupted in early recovery, and poor sleep feeds irritability
and cravings. You can't force sleep, but you can set the stage:</p>
<ul>
  <li>Keep consistent sleep and wake times, even on weekends.</li>
  <li>Wind down with a screen-free routine before bed.</li>
  <li>Cut caffeine in the afternoon and keep your room dark and cool.</li>
  <li>Be patient &mdash; sleep usually improves over the first months.</li>
</ul>

<h2>Nutrition</h2>
<p>Recovery often comes with depleted nutrition and unstable blood sugar, which can
masquerade as anxiety or cravings.</p>
<ul>
  <li>Eat regular meals rather than skipping and crashing.</li>
  <li>Favor protein, whole grains, fruit, and vegetables for steady energy.</li>
  <li>Stay hydrated &mdash; thirst is easy to mistake for a craving.</li>
  <li>Go easy on yourself; small, steady improvements beat a perfect diet.</li>
</ul>

<h2>Exercise</h2>
<p>Movement boosts mood, reduces stress, improves sleep, and gives cravings
somewhere to go. You don't need a gym:</p>
<ul>
  <li>Start with a daily ten-minute walk.</li>
  <li>Pick something you enjoy &mdash; it only works if you keep doing it.</li>
  <li>Use exercise as a coping tool: a walk is a great response to an urge.</li>
</ul>
<p>None of this has to be perfect. Stacking small, consistent habits is what
rebuilds a body &mdash; and a life &mdash; over time.</p>
""" + SAFETY),

    # ---- Family & Friends ----
    ('family',
     'How to Support a Loved One in Recovery Without Enabling',
     'support-loved-one-without-enabling',
     'The difference between support and enabling, and how to actually help.',
     'How to support a loved one in recovery without enabling. Learn the difference '
     'between helping and enabling, how to communicate, and how to take care of '
     'yourself too.',
     """
<h2>Support and enabling are not the same thing</h2>
<p>When someone you love is in recovery, you want to help &mdash; but it's easy to
slip into <em>enabling</em>, which means protecting them from the consequences of
their behavior in a way that quietly makes it easier to keep using. Support helps
the person; enabling protects the addiction. The line isn't always obvious, and
caring people cross it with the best intentions.</p>

<h2>What support looks like</h2>
<ul>
  <li>Listening without lecturing or trying to fix everything.</li>
  <li>Encouraging treatment, meetings, and healthy routines.</li>
  <li>Celebrating milestones and noticing effort, not just outcomes.</li>
  <li>Being honest about how their behavior affects you.</li>
</ul>

<h2>What enabling looks like</h2>
<ul>
  <li>Covering for them &mdash; making excuses, paying debts, smoothing over
  consequences.</li>
  <li>Giving money that may fund use.</li>
  <li>Taking on their responsibilities so they don't have to.</li>
  <li>Staying silent to keep the peace.</li>
</ul>

<h2>How to help without enabling</h2>
<ol>
  <li><strong>Separate the person from the behavior.</strong> You can love someone
  and still refuse to support the addiction.</li>
  <li><strong>Let natural consequences happen.</strong> They're often what
  motivates change.</li>
  <li><strong>Offer help toward recovery, not around it</strong> &mdash; a ride to
  a meeting, yes; cash with no questions, no.</li>
  <li><strong>Take care of yourself.</strong> Support groups for families, like
  Al-Anon or Nar-Anon, exist because you matter too.</li>
</ol>
<p>Following a loved one's recovery from a healthy distance &mdash; staying
connected while keeping your own boundaries &mdash; is one of the most powerful
things you can do for both of you.</p>
""" + SAFETY),

    ('family',
     'Setting Healthy Boundaries With Someone in Active Addiction',
     'healthy-boundaries-active-addiction',
     'Why boundaries help everyone, and how to set and hold them with love.',
     'How to set healthy boundaries with someone in active addiction. What '
     'boundaries are, examples that protect you, and how to hold them with '
     'compassion and consistency.',
     """
<h2>Boundaries are care, not punishment</h2>
<p>A boundary is a limit you set to protect your own wellbeing &mdash; not a
threat or a way to control someone else. When a loved one is in active addiction,
clear boundaries protect your peace, your finances, and your relationships, and
they often do more to encourage change than pleading ever could. Boundaries are an
act of love, including love for yourself.</p>

<h2>What healthy boundaries sound like</h2>
<ul>
  <li>&ldquo;I won't give you money, but I'll help you get to treatment.&rdquo;</li>
  <li>&ldquo;You're welcome here when you're sober. If you're using, you'll need
  to leave.&rdquo;</li>
  <li>&ldquo;I love you, and I can't have this conversation when you're high.&rdquo;</li>
  <li>&ldquo;I need you to call before coming over.&rdquo;</li>
</ul>
<p>Notice the pattern: each one is about what <em>you</em> will and won't do, not
about commanding the other person.</p>

<h2>How to hold them</h2>
<ol>
  <li><strong>Be specific and calm.</strong> State the boundary plainly, without a
  speech or an argument.</li>
  <li><strong>Mean what you say.</strong> Only set consequences you're willing to
  follow through on &mdash; a boundary you don't hold teaches people to ignore it.</li>
  <li><strong>Expect pushback.</strong> Guilt-trips and anger are common at first.
  Holding steady is the hard part, and the important part.</li>
  <li><strong>Get support.</strong> Family groups and a therapist can help you set
  boundaries and stick to them.</li>
</ol>

<h2>Boundaries can change as things change</h2>
<p>Setting limits doesn't mean giving up on someone. You can keep the door open to
recovery while closing it to behavior that harms you. Consistency &mdash; not
perfection &mdash; is what makes boundaries work.</p>
""" + SAFETY),

    # ---- Professional Help ----
    ('professional',
     'Types of Addiction Treatment Explained: Detox, Rehab, IOP, and Therapy',
     'types-of-addiction-treatment-explained',
     'A plain-language guide to the levels of addiction treatment and what each involves.',
     'Addiction treatment options explained in plain language: medical detox, '
     'inpatient rehab, partial hospitalization, intensive outpatient (IOP), '
     'outpatient therapy, and medication-assisted treatment.',
     """
<h2>Treatment isn't one-size-fits-all</h2>
<p>Addiction treatment comes in different levels of intensity, usually described as
a &ldquo;continuum of care.&rdquo; Many people move between levels over time
&mdash; starting more intensive and stepping down as they stabilize. Knowing the
options makes it far easier to ask for the right kind of help.</p>

<h2>The main levels of care</h2>
<h3>Medical detox</h3>
<p>Short-term, medically supervised withdrawal management. For some substances
(like alcohol and benzodiazepines) withdrawal can be dangerous, so detox should be
medically supervised. Detox manages withdrawal &mdash; it's a starting point, not
treatment by itself.</p>
<h3>Inpatient / residential rehab</h3>
<p>Living at a facility full-time, typically for a few weeks to a few months, with
structured therapy, medical support, and a substance-free environment. Best for
severe addiction or when home isn't safe for recovery.</p>
<h3>Partial hospitalization (PHP)</h3>
<p>Intensive day treatment &mdash; several hours a day, most days of the week
&mdash; while living at home or in sober housing.</p>
<h3>Intensive outpatient (IOP)</h3>
<p>Several sessions a week of group and individual therapy, designed to fit around
work or family. A common step-down from rehab or step-up from standard therapy.</p>
<h3>Outpatient therapy</h3>
<p>Regular one-on-one or group counseling, often weekly. Good for milder cases or
ongoing maintenance.</p>
<h3>Medication-assisted treatment (MAT)</h3>
<p>FDA-approved medications (for example, for opioid or alcohol use disorder)
combined with counseling. MAT is evidence-based and, for many people, life-saving.</p>

<h2>How to choose a level</h2>
<p>The right starting point depends on the substance, how severe the use is,
physical and mental health, and your support at home. A doctor or a treatment
center's intake team can assess this with you. If cost is a concern, the
<strong>SAMHSA National Helpline (1-800-662-4357)</strong> offers free, confidential
referrals 24/7.</p>
""" + SAFETY),

    ('professional',
     'How to Choose a Therapist or Treatment Center',
     'how-to-choose-therapist-treatment-center',
     'Practical questions to ask and red flags to watch for when getting professional help.',
     'How to choose an addiction therapist or treatment center: the right questions '
     'to ask, credentials to look for, red flags to avoid, and free ways to find '
     'reputable help.',
     """
<h2>Finding the right help is worth getting right</h2>
<p>Professional support can make an enormous difference in recovery &mdash; but
quality varies, and some programs are better than others. A little homework up
front helps you find care that's reputable, evidence-based, and right for you.</p>

<h2>What to look for</h2>
<ul>
  <li><strong>Proper credentials and licensing.</strong> Look for licensed
  clinicians and accredited facilities.</li>
  <li><strong>Evidence-based methods.</strong> Approaches like CBT, motivational
  interviewing, and medication-assisted treatment have strong research behind
  them.</li>
  <li><strong>Experience with your situation.</strong> Specific substances,
  co-occurring mental health conditions, trauma, or your age group.</li>
  <li><strong>A good personal fit.</strong> With a therapist especially, feeling
  safe and understood matters as much as technique.</li>
</ul>

<h2>Questions to ask</h2>
<ol>
  <li>What are your credentials and experience with addiction?</li>
  <li>What treatment approaches do you use, and why?</li>
  <li>What does a typical course of treatment look like?</li>
  <li>How do you handle relapse?</li>
  <li>What are the costs, and do you take my insurance?</li>
</ol>

<h2>Red flags to avoid</h2>
<ul>
  <li>Guarantees of a quick or permanent &ldquo;cure.&rdquo;</li>
  <li>Pressure to commit immediately or pay large sums up front.</li>
  <li>One-size-fits-all programs that ignore your specific needs.</li>
  <li>Aggressive marketing or paid referral &ldquo;hotlines&rdquo; that won't name
  the facility.</li>
</ul>

<h2>Free ways to find reputable help</h2>
<p>The <strong>SAMHSA National Helpline (1-800-662-4357)</strong> and its online
treatment locator offer free, confidential referrals 24/7. Your primary care
doctor can also be a trustworthy starting point and referral source. Take your
time &mdash; asking questions is your right, and a good provider will welcome
them.</p>
""" + SAFETY),
]


class Command(BaseCommand):
    help = 'Draft new written resources to fill the empty resource categories'

    def handle(self, *args, **options):
        # Ensure categories exist.
        cats = {}
        for slug, name, icon, desc, order in CATEGORIES:
            cat, _ = ResourceCategory.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'icon': icon, 'description': desc, 'order': order},
            )
            cats[slug] = cat

        # Ensure an "Article" resource type exists for written guides.
        article_type, _ = ResourceType.objects.get_or_create(
            slug='article',
            defaults={'name': 'Article', 'color': '#3B82F6', 'icon': '📖'},
        )

        created = updated = 0
        for cat_slug, title, slug, desc, meta, content in RESOURCES:
            obj, was_created = Resource.objects.update_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'category': cats[cat_slug],
                    'resource_type': article_type,
                    'description': desc,
                    'meta_description': meta,
                    'content': content.strip(),
                    'interaction_type': 'static',
                    'access_level': 'free',
                    'is_active': True,
                },
            )
            created += was_created
            updated += not was_created
            tag = 'Created' if was_created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'  {tag}: [{cat_slug}] {title}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created} created, {updated} updated.'
        ))
