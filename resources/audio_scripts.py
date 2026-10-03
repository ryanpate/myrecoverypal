"""Scripts for the audio library.

Every session is written here, in code, so the words are reviewed in PRs
like any other copy. A script is a list of parts: strings are spoken by the
AI voice (ElevenLabs, see management command `generate_audio`), and P(n) is
n seconds of silence stitched in between (resources/audio_mp3.py).

Narrations of the 30 daily reflections are built from resources/reflections.py
by `reflection_script`, so they never drift from the written readings.

Access (resources/audio_views.py):
  * sessions marked free=True are free for everyone. These are the
    crisis-adjacent tools (urge surfing, breathing, grounding, craving reset):
    safety tools are never paywalled.
  * other sessions are Premium.
  * a reflection narration follows its reading: free on the day it is
    today's reflection, Premium otherwise.

All text is original. No medical claims; breathing exercises tell people to
breathe normally if they feel lightheaded.
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Union


@dataclass(frozen=True)
class P:
    """Silence, in seconds."""
    seconds: float


Part = Union[str, P]


@dataclass(frozen=True)
class Session:
    slug: str
    title: str
    category: str
    description: str
    free: bool
    parts: Tuple[Part, ...] = field(default=())


CATEGORIES = {
    'cravings': 'Craving help',
    'calm': 'Breathing & calm',
    'sleep': 'Sleep',
    'morning': 'Morning',
    'reflections': 'Daily reflections, read aloud',
}

CRISIS_LINE = ("If you're in danger, or thinking about harming yourself, please pause this "
               "and call or text 9 8 8, or call 9 1 1.")


def _breath_cycle():
    return ["Breathe in quietly through your nose.", P(3.5),
            "Hold.", P(6), "And breathe out slowly through your mouth.", P(7.5)]


SESSIONS = [
    Session(
        slug='urge-surfing',
        title='Urge surfing',
        category='cravings',
        description='Ride out a craving like a wave: notice it rise, peak and pass, without acting on it. About 7 minutes.',
        free=True,
        parts=(
            "This is urge surfing. If a craving is with you right now, you're in the right place.",
            P(1.5), CRISIS_LINE, P(2),
            "Find a position where you can stay still for a few minutes. Sitting or lying down, "
            "whatever is easiest. You don't need to fight anything. You only need to notice.", P(4),
            "Take one slow breath in.", P(3), "And let it go.", P(4),
            "Now turn your attention toward the craving itself. Not the thoughts about it. "
            "The feeling of it.", P(4),
            "Where do you feel it in your body? Your chest. Your stomach. Your mouth, your hands, "
            "your jaw. Just find the place where it's strongest.", P(8),
            "Notice what it feels like there. Is it tight, or hot, or restless, or heavy? "
            "There's no right answer. Just describe it to yourself.", P(10),
            "A craving is like a wave in the ocean. It builds, it rises, it reaches a peak, "
            "and then it falls. Every craving you have ever had has ended. This one will too.", P(6),
            "Imagine you're on a surfboard, riding this wave instead of being pulled under. "
            "Your breath is the board.", P(4),
            "Breathe in.", P(3.5), "And out.", P(5),
            "Breathe in.", P(3.5), "And out.", P(6),
            "Check in with the feeling again. Has it changed at all? Bigger, smaller, moved somewhere "
            "else? Just notice.", P(10),
            "If it's getting stronger, that's all right. Waves get bigger before they break. "
            "Keep breathing. You're still on the board.", P(8),
            "You might notice thoughts like, I need this, or just once won't hurt. You don't have "
            "to argue with them. Let them be thoughts, like clouds passing over the water.", P(10),
            "Breathe in.", P(3.5), "And out.", P(6),
            "Bring your attention back to the place in your body where you felt the craving. "
            "Describe it again. Where is it now? How strong, on a scale of one to ten?", P(12),
            "Stay with it a little longer. Riding out a wave teaches your brain something important: "
            "that you can feel an urge and still choose what you do.", P(10),
            "Breathe in.", P(3.5), "And out.", P(8),
            "Notice what's happened to the wave. For many people, by now it has started to settle. "
            "If it hasn't, you can play this again, or step outside, or call someone.", P(6),
            "Whatever it feels like right now, you stayed with it instead of acting on it. "
            "That counts. That is exactly the skill.", P(4),
            "When you're ready, open your eyes if they were closed, and take one more full breath.", P(4),
            "Well done.",
        ),
    ),
    Session(
        slug='breathing-4-7-8',
        title='4-7-8 breathing',
        category='calm',
        description='A slow breathing pattern to calm a racing mind or body: in for 4, hold for 7, out for 8. About 3 minutes.',
        free=True,
        parts=(
            "This is four seven eight breathing. It's a simple way to slow everything down.", P(1.5),
            "You'll breathe in for a count of four, hold for seven, and breathe out slowly for eight. "
            "If at any point you feel lightheaded, just go back to breathing normally.", P(3),
            "Let your shoulders drop. Rest the tip of your tongue just behind your top teeth, "
            "if that's comfortable.", P(3),
            "First, breathe all the way out.", P(4),
            *_breath_cycle(), *_breath_cycle(), *_breath_cycle(), *_breath_cycle(),
            "Now let your breathing return to its own natural rhythm.", P(6),
            "Notice how your body feels compared to a few minutes ago. Even a small shift matters.", P(4),
            "You can come back to this any time, anywhere. Nobody even has to know you're doing it.",
        ),
    ),
    Session(
        slug='grounding-5-4-3-2-1',
        title='5-4-3-2-1 grounding',
        category='calm',
        description='Bring yourself back to the present moment using your five senses. Helpful for anxiety, panic or a spinning mind. About 4 minutes.',
        free=True,
        parts=(
            "This is a grounding exercise. It uses your senses to bring you back to right here, "
            "right now.", P(1.5), CRISIS_LINE, P(2),
            "Keep your eyes open for this one. Take a slow breath in.", P(3), "And out.", P(4),
            "Look around you and find five things you can see. Name them to yourself, slowly. "
            "A color. A shape. Something small you hadn't noticed.", P(15),
            "Now four things you can feel. Your feet on the floor. The weight of your body in the "
            "chair. The fabric of your clothes. The air on your skin.", P(14),
            "Three things you can hear. Near or far. A hum, a car, your own breathing.", P(13),
            "Two things you can smell. If nothing stands out, notice what the air smells like, "
            "or remember a smell you like.", P(11),
            "And one thing you can taste, or one thing you're grateful for right now.", P(9),
            "Take another slow breath in.", P(3), "And out.", P(5),
            "You're here. In this room, in this moment. Whatever was racing a few minutes ago, "
            "you've given yourself a little space from it.", P(4),
            "You can do this any time things feel like too much.",
        ),
    ),
    Session(
        slug='craving-reset',
        title='3-minute craving reset',
        category='cravings',
        description='A short reset for when a craving hits and you only have a few minutes. About 3 minutes.',
        free=True,
        parts=(
            "Three minutes. That's all this takes. Let's buy you some time.", P(1.5),
            "First, if you can, put a little distance between you and whatever you'd use. "
            "Another room, outside, anywhere else. I'll wait.", P(8),
            "Now, one long breath in.", P(4), "And all the way out.", P(6),
            "Again. In.", P(4), "And out.", P(6),
            "Ask yourself four quick questions. Am I hungry?", P(3), "Am I angry?", P(3),
            "Am I lonely?", P(3), "Am I tired?", P(4),
            "If any of those is a yes, that's something you can deal with directly, in the next "
            "ten minutes, without using. A snack. A glass of water. A text to someone. A rest.", P(6),
            "Now picture the next few hours if you use. Not just the first minute. The rest of the "
            "night, and tomorrow morning.", P(8),
            "And picture tomorrow morning if you don't.", P(8),
            "Cravings rise and fall. This one will pass, usually faster than it feels like it will.", P(3),
            "Pick one thing to do right now. Call someone, step outside, drink some water, or play "
            "the urge surfing session. Go and do it now.",
        ),
    ),
    Session(
        slug='body-scan',
        title='Body scan',
        category='calm',
        description='A slow, guided scan from head to toe to release tension and settle your nervous system. About 10 minutes.',
        free=False,
        parts=(
            "Welcome to this body scan. Find a comfortable position, lying down or sitting, "
            "and let your eyes close if that feels okay.", P(4),
            "Take a slow breath in.", P(3.5), "And let it go.", P(5),
            "There's nothing to achieve here. You're simply going to notice each part of your body, "
            "one at a time, and let it soften if it wants to.", P(5),
            "Start with the top of your head. Notice any sensation there. Tingling, warmth, "
            "or nothing at all. All of it is fine.", P(12),
            "Move your attention to your forehead. If it's tight, let it smooth out.", P(10),
            "Your eyes, and the small muscles around them. Let them rest.", P(10),
            "Your jaw. Many of us hold a lot of tension here. Let your teeth part slightly "
            "and your jaw hang loose.", P(12),
            "Your neck and throat.", P(10),
            "Your shoulders. Let them drop away from your ears. Maybe a little further.", P(12),
            "Your upper arms, your elbows, your forearms.", P(10),
            "Your hands. Your palms, your fingers, your thumbs. Notice any warmth or pulsing.", P(12),
            "Bring your attention to your chest. Notice it rising and falling with each breath, "
            "without changing anything.", P(14),
            "Your stomach. If it's tight, let it soften. Let it move freely as you breathe.", P(14),
            "Your upper back, and your lower back. Let them be supported by whatever is beneath you.", P(12),
            "Your hips.", P(10), "Your thighs.", P(10), "Your knees.", P(8),
            "Your calves and your shins.", P(10),
            "Your ankles, your feet, and all ten toes.", P(12),
            "Now notice your whole body at once, from the top of your head to the soles of your feet. "
            "Breathing. Resting. Here.", P(15),
            "If your mind wandered during this, that's completely normal. Each time you noticed and "
            "came back, you were practicing.", P(6),
            "Take a deeper breath in.", P(4), "And let it go.", P(5),
            "When you're ready, wiggle your fingers and toes, and slowly open your eyes.",
        ),
    ),
    Session(
        slug='sleep-wind-down',
        title='Sleep wind-down',
        category='sleep',
        description='A slow, quiet wind-down to help you let go of the day and drift toward sleep. About 10 minutes.',
        free=False,
        parts=(
            "This is a wind-down for sleep. Get comfortable in bed, and let the room be as dark "
            "and quiet as you can make it.", P(5),
            "You don't need to try to fall asleep. Trying usually makes it harder. Just rest, "
            "and let sleep come when it's ready.", P(6),
            "Breathe in slowly.", P(4), "And out, even more slowly.", P(7),
            "Again.", P(4), "And out.", P(8),
            "Let today be finished. Whatever happened, whatever didn't get done, it can wait "
            "until tomorrow. Right now, there's nothing you need to fix.", P(10),
            "If you stayed sober today, that is a good day's work. If today was hard, you're still "
            "here, and tomorrow is a new start.", P(10),
            "Let the weight of your body sink into the bed. Your head heavy on the pillow.", P(10),
            "Your shoulders heavy.", P(8), "Your arms heavy.", P(8),
            "Your back, your hips, your legs. Heavy and warm and still.", P(14),
            "If a thought comes, about today or tomorrow, notice it, and imagine setting it down "
            "on a shelf beside the bed. It'll be there in the morning if you need it.", P(14),
            "Breathe in.", P(4), "And out.", P(9),
            "Picture a place where you feel completely safe and calm. Somewhere real or imagined. "
            "A beach, a forest, a quiet room.", P(10),
            "Notice what you'd see there.", P(12), "What you'd hear.", P(12),
            "The temperature of the air.", P(12),
            "Let yourself stay there. There's nowhere else you need to be.", P(20),
            "Breathe in.", P(4), "And out.", P(10),
            "You can let my voice fade now. Rest well.", P(20),
        ),
    ),
    Session(
        slug='morning-intention',
        title='Morning intention',
        category='morning',
        description='A short start to the day: arrive, choose your intention, and remember why you are doing this. About 4 minutes.',
        free=False,
        parts=(
            "Good morning. Before the day gets busy, let's take a few minutes for you.", P(2),
            "Sit comfortably, and take a slow breath in.", P(3.5), "And out.", P(5),
            "Notice how you're feeling this morning. Rested, tired, hopeful, anxious. "
            "Whatever it is, just notice it without judging.", P(8),
            "Bring to mind your reason. The person, the hope, the life you're working toward. "
            "Hold it in your mind for a moment.", P(10),
            "Now think about the day ahead. Is there a time, a place or a person that might be "
            "hard today?", P(8),
            "What's one thing you could do to make that moment a little easier?", P(10),
            "Choose an intention for today. Just a few words. Something like, I'll be patient "
            "with myself. Or, I'll ask for help if I need it. Or simply, I'll stay sober today.", P(10),
            "Say your intention to yourself, quietly.", P(6),
            "One more breath in.", P(3.5), "And out.", P(4),
            "You don't have to get the whole day right. Just this next hour. Then the next one.", P(2),
            "Go gently today.",
        ),
    ),
]

SESSIONS_BY_SLUG = {s.slug: s for s in SESSIONS}

REFLECTION_SLUG_PREFIX = 'reflection-'


def reflection_script(reflection):
    """Narration parts for a daily reflection (resources/reflections.py)."""
    parts: List[Part] = [reflection.title, P(1.5)]
    for paragraph in reflection.paragraphs:
        parts += [paragraph, P(1.2)]
    parts += [P(0.8), "A question to sit with today.", P(1), reflection.prompt, P(4)]
    return tuple(parts)


def all_scripts():
    """[(slug, title, category, description, free, parts, reflection_slug)] for generation."""
    from .reflections import REFLECTIONS
    out = [(s.slug, s.title, s.category, s.description, s.free, s.parts, '') for s in SESSIONS]
    for r in REFLECTIONS:
        out.append((REFLECTION_SLUG_PREFIX + r.slug, r.title, 'reflections',
                    f'The "{r.title}" reflection, read aloud.', False, reflection_script(r), r.slug))
    return out


def transcript(parts):
    return '\n\n'.join(p for p in parts if isinstance(p, str))


def spoken_characters(parts):
    return sum(len(p) for p in parts if isinstance(p, str))
