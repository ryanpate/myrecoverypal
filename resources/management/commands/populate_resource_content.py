"""Populate on-page body content and SEO meta descriptions for the core
recovery resources.

These detail pages previously rendered only a title and a one-sentence
description, which reads as thin content to search engines. This command fills
the ``content`` (rendered as HTML on the detail page) and ``meta_description``
fields with genuine, useful guidance. It is idempotent — re-running updates the
same resources by slug, so it is safe to run on production after deploy.

    python manage.py populate_resource_content
"""
from django.core.management.base import BaseCommand

from resources.models import Resource


# slug -> {meta_description, content (HTML)}
RESOURCE_CONTENT = {
    'relapse-prevention-plan': {
        'meta_description': (
            'Build a personalized relapse prevention plan. Learn to spot early '
            'warning signs, map your triggers, and prepare a step-by-step response '
            'for high-risk moments. Free template and guide.'
        ),
        'content': """
<h2>What a relapse prevention plan does</h2>
<p>Relapse rarely starts with a drink or a drug. It starts days or weeks earlier
&mdash; in your thoughts, moods, and routines. A relapse prevention plan is a
written, personal early-warning system: it names the situations that put you at
risk, the signs that you're drifting, and the exact steps you'll take before a
craving becomes a decision. Writing it down when you're steady means you don't
have to think clearly in the moment you're least able to.</p>

<h2>Know the early warning signs</h2>
<p>Most people move through recognizable stages before a physical relapse.
Catching them early is the whole point of the plan.</p>
<ul>
  <li><strong>Emotional drift:</strong> bottling up feelings, isolating, skipping
  meetings or check-ins, poor sleep, neglecting self-care.</li>
  <li><strong>Mental bargaining:</strong> romanticizing past use, thinking
  &ldquo;just once,&rdquo; spending time around old people or places, planning
  ways it could work.</li>
  <li><strong>Physical relapse:</strong> the use itself &mdash; which is almost
  always the last link in a long chain, not the first.</li>
</ul>
<p>A useful shortcut is <strong>HALT</strong>: when you notice a craving, ask
whether you are <em>Hungry, Angry, Lonely, or Tired</em>. Those four states drive
a surprising share of relapses, and each has a simple fix.</p>

<h2>Build your plan, section by section</h2>
<h3>1. My personal triggers</h3>
<p>List the people, places, emotions, and times of day that reliably raise your
risk. Be specific &mdash; &ldquo;Friday after work&rdquo; is more useful than
&ldquo;stress.&rdquo;</p>
<h3>2. My early warning signs</h3>
<p>Write the thoughts and behaviors <em>you</em> show before a slip. Ask someone
who knows you well; others often spot the pattern before you do.</p>
<h3>3. My coping strategies</h3>
<p>For each trigger, name what you'll do instead: call your sponsor, go for a
walk, use a breathing exercise, leave the situation, log a craving in your
tracker. Match a concrete action to each risk.</p>
<h3>4. My support contacts</h3>
<p>List names and numbers you can reach right now &mdash; a sponsor, a trusted
friend, a meeting hotline. Add the <strong>988 Suicide &amp; Crisis
Lifeline</strong> (call or text 988) for moments that feel unsafe.</p>
<h3>5. My reasons for recovery</h3>
<p>Write why you started. In a craving, &ldquo;play the tape forward&rdquo;:
picture not just the first use but the hours and days that follow it.</p>

<h2>Keep it where you'll use it</h2>
<p>A plan in a drawer doesn't help. Keep a copy on your phone, share it with one
person who has your back, and revisit it whenever your life changes &mdash; a new
job, a move, a hard anniversary. Your plan should grow with your recovery.</p>

<p><em>This guide is educational and is not a substitute for professional
treatment. If you're in crisis, call or text 988.</em></p>
""",
    },
    'daily-recovery-checklist': {
        'meta_description': (
            'A simple daily recovery checklist to build structure and protect your '
            'sobriety. Morning, midday, and evening habits that keep you grounded '
            'one day at a time. Free printable guide.'
        ),
        'content': """
<h2>Why daily structure protects recovery</h2>
<p>Early recovery thrives on routine. When your days have a predictable shape,
there's less room for the boredom, isolation, and decision-fatigue that
cravings feed on. A daily checklist turns &ldquo;stay sober&rdquo; &mdash; which
is huge and abstract &mdash; into a handful of small, doable actions you can
actually check off. Progress you can see builds momentum.</p>

<h2>Morning: set the tone</h2>
<ul>
  <li>Log your sobriety day and notice the number growing.</li>
  <li>Do a two-minute check-in: how's my mood, what's my craving level today?</li>
  <li>Name one intention for the day &mdash; small and specific.</li>
  <li>Eat something and drink water (remember HALT &mdash; Hungry, Angry, Lonely,
  Tired).</li>
</ul>

<h2>Midday: stay connected</h2>
<ul>
  <li>Reach out to one person &mdash; a text to a sober friend counts.</li>
  <li>Move your body, even a ten-minute walk.</li>
  <li>Check in with your feelings instead of pushing through on autopilot.</li>
  <li>If a craving hits, pause and use a coping skill before reacting.</li>
</ul>

<h2>Evening: reflect and reset</h2>
<ul>
  <li>Write down one thing you're grateful for.</li>
  <li>Note one win, however small, and one thing that was hard.</li>
  <li>Plan tomorrow's first step so morning-you isn't starting from zero.</li>
  <li>Protect your sleep &mdash; it's one of the strongest relapse-prevention
  tools you have.</li>
</ul>

<h2>Make it yours</h2>
<p>This is a starting template, not a rulebook. Keep the items that help, cut the
ones that don't, and add what matters for your program &mdash; a meeting, prayer
or meditation, medication, a call with your sponsor. The goal isn't a perfect
day; it's showing up for the small things that, stacked together, add up to a
recovery. Miss an item? Check the next one. One day at a time, one box at a
time.</p>

<p><em>Educational content only, not medical advice. In crisis, call or text
988.</em></p>
""",
    },
    'coping-skills-for-cravings': {
        'meta_description': (
            'Evidence-informed coping skills to ride out cravings: urge surfing, '
            'the 4 Ds, grounding, and HALT. Practical techniques you can use the '
            'moment a craving hits. Free interactive checklist and PDF.'
        ),
        'content': """
<h2>Cravings pass &mdash; your job is to outlast them</h2>
<p>A craving feels like it will keep climbing forever, but it won't. Urges tend
to rise, peak, and fall within about 15&ndash;30 minutes, like a wave. You don't
have to fight the wave or be carried off by it &mdash; you just have to stay
standing until it breaks. These skills buy you that time.</p>

<h2>Urge surfing</h2>
<p>Instead of resisting the craving, observe it. Notice where you feel it in your
body, how intense it is on a scale of 1&ndash;10, and how it shifts minute to
minute. Breathe slowly and watch it like weather passing through. Naming a
craving as a temporary physical sensation &mdash; rather than a command &mdash;
takes away much of its power.</p>

<h2>The 4 Ds</h2>
<ul>
  <li><strong>Delay:</strong> tell yourself you'll wait 15 minutes before doing
  anything. Most urges weaken in that window.</li>
  <li><strong>Distract:</strong> change your activity and your scenery &mdash; a
  walk, a shower, a task that uses your hands.</li>
  <li><strong>Deep breathe:</strong> inhale for four counts, hold for four,
  exhale for six. Longer exhales calm the nervous system.</li>
  <li><strong>De-catastrophize:</strong> remind yourself the feeling is temporary
  and you've survived it before.</li>
</ul>

<h2>Check HALT</h2>
<p>When a craving spikes, ask whether you're <strong>Hungry, Angry, Lonely, or
Tired</strong>. These four states masquerade as cravings constantly. Eat, vent to
someone, connect, or rest &mdash; and the urge often deflates on its own.</p>

<h2>Grounding for the worst moments</h2>
<p>If a craving comes with panic or racing thoughts, try the <strong>5-4-3-2-1</strong>
technique: name five things you can see, four you can touch, three you can hear,
two you can smell, and one you can taste. It pulls your attention out of the urge
and back into the present.</p>

<h2>Play the tape forward</h2>
<p>Cravings sell you the first five minutes of using and hide the rest. Walk the
story all the way to the end &mdash; the consequences, the guilt, the lost days,
having to reset your counter. Then call someone before you decide anything. You
never have to white-knuckle a craving alone.</p>

<p><em>These techniques support recovery but don't replace professional care. If
you're in crisis, call or text 988.</em></p>
""",
    },
    'trigger-identification-worksheet': {
        'meta_description': (
            'Identify your personal addiction triggers, internal and external, '
            'so you can plan around them. A practical worksheet and guide to '
            'mapping the people, places, and feelings that raise your risk. Free.'
        ),
        'content': """
<h2>You can't avoid what you haven't named</h2>
<p>A trigger is anything that sets off a craving or a thought about using. Some
are obvious; many are subtle and personal. The point of mapping them isn't to
live in fear &mdash; it's the opposite. Once a trigger is named, it becomes
something you can plan for, avoid when possible, and face with a strategy when
you can't. Vague risk is scary; specific risk is manageable.</p>

<h2>External triggers</h2>
<p>These come from your environment &mdash; the people, places, and things tied to
past use.</p>
<ul>
  <li><strong>People:</strong> old using friends, certain family members,
  anyone you associate with the behavior.</li>
  <li><strong>Places:</strong> bars, a specific neighborhood, the route home that
  passes a familiar spot.</li>
  <li><strong>Things &amp; cues:</strong> paydays, certain music, the smell of
  alcohol, holidays, even particular times of day.</li>
</ul>

<h2>Internal triggers</h2>
<p>These come from within &mdash; emotional and physical states that nudge you
toward using.</p>
<ul>
  <li><strong>Difficult emotions:</strong> stress, boredom, loneliness, anger,
  shame, grief.</li>
  <li><strong>&ldquo;Positive&rdquo; states too:</strong> celebration, confidence,
  &ldquo;I've earned it&rdquo; &mdash; these catch people off guard.</li>
  <li><strong>Physical states:</strong> exhaustion, hunger, pain, or being unwell.
  (Remember HALT.)</li>
</ul>

<h2>How to map your triggers</h2>
<ol>
  <li>Think back to past cravings or slips. What was happening just before &mdash;
  where were you, who were you with, what were you feeling?</li>
  <li>Write each trigger down and rate its intensity from 1 to 10.</li>
  <li>Sort them into &ldquo;avoid&rdquo; (cut out where you can) and
  &ldquo;prepare for&rdquo; (unavoidable, so plan a response).</li>
  <li>For each high-risk trigger, write one concrete coping action you'll take
  when it shows up.</li>
</ol>

<h2>Turn the list into a plan</h2>
<p>Your trigger map feeds directly into your relapse prevention plan. Triggers you
can avoid, avoid early. Triggers you can't &mdash; a stressful job, a family
event &mdash; get a rehearsed response: who you'll call, what you'll do, how
you'll leave if you need to. Knowing your triggers is the first half of staying
ready; having a plan for them is the second.</p>

<p><em>Educational content, not a clinical assessment. If you're in crisis, call
or text 988.</em></p>
""",
    },
}


class Command(BaseCommand):
    help = 'Populate on-page content and meta descriptions for core recovery resources'

    def handle(self, *args, **options):
        updated = 0
        missing = []
        for slug, data in RESOURCE_CONTENT.items():
            try:
                resource = Resource.objects.get(slug=slug)
            except Resource.DoesNotExist:
                missing.append(slug)
                continue

            resource.content = data['content'].strip()
            resource.meta_description = data['meta_description']
            resource.save(update_fields=['content', 'meta_description'])
            updated += 1
            self.stdout.write(self.style.SUCCESS(f'  Updated: {resource.title}'))

        self.stdout.write(self.style.SUCCESS(f'\nUpdated {updated} resource(s).'))
        if missing:
            self.stdout.write(self.style.WARNING(
                f'Not found (skipped): {", ".join(missing)}'
            ))
