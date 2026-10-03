"""Scripts for the audio library.

Every session is written here, in code, so the words are reviewed in PRs
like any other copy. A script is a list of parts: strings are spoken by the
AI voice (ElevenLabs, see management command `generate_audio`), and P(n) is
n seconds of silence stitched in between (resources/audio_mp3.py).

Narrations of the 30 daily reflections are built from resources/reflections.py
by `reflection_script`, so they never drift from the written readings.

Access (resources/audio_views.py):
  * sessions marked free=True are free for everyone. These are the
    crisis-adjacent tools (urge surfing, breathing, grounding, craving reset,
    before a social event, after a slip): safety tools are never paywalled.
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
        description='Ride out a craving like a wave: notice it rise, peak and pass, without acting on it. About 6 minutes.',
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
        description='Bring yourself back to the present moment using your five senses. Helpful for anxiety, panic or a spinning mind. About 3 minutes.',
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
        description='A short reset for when a craving hits and you only have a few minutes. Under 3 minutes.',
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
        description='A slow, guided scan from head to toe to release tension and settle your nervous system. About 6 minutes.',
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
        description='A slow, quiet wind-down to help you let go of the day and drift toward sleep. About 5 minutes.',
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
        description='A short start to the day: arrive, choose your intention, and remember why you are doing this. About 3 minutes.',
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
    Session(
        slug='social-event-prep',
        title='Before a social event',
        category='cravings',
        description='Get ready for a party, wedding, work drinks or family dinner: a plan, a drink order, an exit, and a reason. About 4 minutes.',
        free=True,
        parts=(
            "This is for the few minutes before a social event. A party, a dinner, a wedding, "
            "drinks after work. Somewhere there'll be alcohol, or people you used to use with.", P(2),
            CRISIS_LINE, P(2),
            "Take a slow breath in.", P(3.5), "And out.", P(5),
            "First, notice how you feel about going. Excited, nervous, dreading it. "
            "All of that is normal. You don't have to feel ready to go well prepared.", P(8),
            "Let's make a plan. Picture walking in the door. What's the first thing you'll do? "
            "Find the host. Find a friend. Get a drink in your hand that you chose.", P(10),
            "Decide your drink now, so you don't have to decide in the moment. Sparkling water "
            "with lime. A soda. A mocktail. Something you actually like.", P(8),
            "Now your answer, for when someone offers you a drink or asks why you're not having one. "
            "Keep it short. No thanks, I'm good. I'm driving. I've got an early start. "
            "You don't owe anyone your story.", P(10),
            "Say your answer to yourself once, quietly, so it's ready.", P(6),
            "Think about who you could text during the event if things get hard. "
            "Maybe let them know now that you might.", P(8),
            "And decide your exit. A time you'll leave by, and how you'll get home. Leaving early "
            "is always allowed. You can go the moment it stops feeling right, without explaining.", P(10),
            "Notice whether there's one part of tonight you're most worried about. A person, "
            "a moment, a certain time of night. What will you do if it happens?", P(10),
            "Now bring to mind why you're doing this. The person, the morning, the life you want. "
            "Hold it for a moment.", P(8),
            "One more breath in.", P(3.5), "And out.", P(5),
            "You have a drink, an answer, a person and an exit. That's a plan. "
            "If you need a minute during the night, step outside, or into the bathroom, "
            "and play the craving reset.", P(3),
            "Go and enjoy what you can. Tomorrow morning, you'll be glad.",
        ),
    ),
    Session(
        slug='after-a-slip',
        title='After a slip',
        category='calm',
        description="For the hours after a slip or relapse: stay safe, stop the shame spiral, and take one next step. About 4 minutes.",
        free=True,
        parts=(
            "If you've slipped, I'm really glad you're here. Pressing play on this was a good thing to do.", P(2),
            CRISIS_LINE, P(2),
            "First, your safety. If you used after a break, even a few days, your body may not "
            "handle what it used to. Please don't use alone. If anyone is hard to wake, or "
            "breathing strangely, call 9 1 1 right away.", P(4),
            "Now, take a slow breath in.", P(3.5), "And out.", P(5),
            "You might be hearing a voice that says, I've ruined everything. I've lost my time. "
            "I might as well keep going. That voice is very common after a slip. "
            "It's also not telling you the truth.", P(8),
            "A slip is a moment. It doesn't erase the days you stayed sober, or the things "
            "you learned in them. Those are still yours.", P(6),
            "Breathe in.", P(3.5), "And out.", P(6),
            "Shame says, I am bad. Guilt says, I did something I don't want to do again. "
            "Shame keeps people stuck. Guilt can point the way forward. "
            "You're allowed to put the shame down.", P(8),
            "Think, gently, about what led up to this. Not to blame yourself. Just to learn. "
            "Were you tired, lonely, stressed, celebrating? Was there a place, or a person?", P(12),
            "Whatever you notice is useful information for next time.", P(4),
            "Now, one next step. Not the whole plan. Just one thing for the next hour. "
            "Drinking some water. Eating something. Getting rid of what's left. Going to sleep.", P(8),
            "And one person. Someone you could tell, a sponsor, a friend, a counselor, a meeting. "
            "You don't have to tell them everything. Just enough not to carry this alone.", P(8),
            "If you want more help, you can call the free national helpline any time, "
            "or talk to your doctor about what support is right for you.", P(4),
            "One more breath in.", P(3.5), "And out.", P(5),
            "Recovery isn't a straight line, and almost everyone who has made it has a day like "
            "this somewhere in their story. Today can be the day you started again.",
        ),
    ),
    Session(
        slug='self-compassion',
        title='Self-compassion for a hard day',
        category='calm',
        description='Talk to yourself the way you would talk to a friend you love. For days full of regret, criticism or shame. About 5 minutes.',
        free=False,
        parts=(
            "This session is for a hard day. A day when the voice in your head has been harsh.", P(2),
            "Get comfortable, and let your eyes close if that feels okay.", P(3),
            "Take a slow breath in.", P(3.5), "And let it go.", P(5),
            "Notice what you've been saying to yourself today. You don't have to repeat it. "
            "Just notice its tone. Is it kind? Is it fair?", P(10),
            "Now imagine a close friend came to you, having the exact same day you've had. "
            "Same mistakes, same feelings. What would you say to them?", P(12),
            "Probably something like, of course this is hard. You're doing your best. "
            "It's going to be okay.", P(6),
            "You deserve that same voice. Let's practice using it.", P(4),
            "If it feels right, place a hand on your chest, or wherever feels comforting. "
            "Feel its warmth.", P(8),
            "Say to yourself, quietly: This is a hard moment.", P(6),
            "Hard moments are part of being human. I'm not the only one.", P(6),
            "May I be kind to myself right now.", P(8),
            "Breathe in.", P(3.5), "And out.", P(6),
            "Bring to mind one thing you did today that took effort. It can be small. "
            "Getting up. Not using. Being honest. Pressing play on this.", P(10),
            "Let yourself give it some credit. Effort counts, even on days that don't go well.", P(6),
            "If there's something you regret, you can hold that too. Ask yourself, what would "
            "help, tomorrow, to make it right or do it differently? Then let the rest go for tonight.", P(12),
            "Breathe in.", P(3.5), "And out.", P(6),
            "Being kind to yourself isn't letting yourself off the hook. It's what gives you the "
            "strength to keep going. People change faster with encouragement than with punishment.", P(5),
            "Take one more slow breath.", P(4), "And when you're ready, open your eyes.", P(2),
            "Go easy on yourself today.",
        ),
    ),
    Session(
        slug='evening-check-out',
        title='Evening check-out',
        category='sleep',
        description='Close the day in a few minutes: what went well, what was hard, what you are grateful for, and one thing for tomorrow. About 4 minutes.',
        free=False,
        parts=(
            "This is your evening check-out. A few minutes to close the day before you rest.", P(2),
            "Sit or lie somewhere comfortable, and take a slow breath in.", P(3.5), "And out.", P(5),
            "Think back over today, from the moment you woke up. Don't analyze it. "
            "Just let it play through quickly, like flipping through photos.", P(12),
            "What's one thing that went well today? Something you did, something that happened, "
            "a moment that felt good.", P(10),
            "Let yourself enjoy that for a moment.", P(5),
            "Now, what was hard today? A craving, a feeling, a conversation, a moment you wish "
            "had gone differently.", P(10),
            "You got through it. Whatever it was, you're here at the end of the day.", P(5),
            "Was there anything you'd like to make right? An apology, a message, a thing left "
            "undone. If there is, decide when you'll do it, and then set it aside for tonight.", P(10),
            "Now three things you're grateful for. Big or small. A person, a meal, a quiet minute, "
            "a bed to sleep in.", P(15),
            "Breathe in.", P(3.5), "And out.", P(6),
            "Look ahead to tomorrow. Is there one thing you'd like to do for your recovery? "
            "A meeting, a call, a walk, a check-in.", P(10),
            "Picture yourself doing it.", P(6),
            "And if you stayed sober today, take a moment to notice that. It's one more day. "
            "That's how all of it is built.", P(6),
            "One more breath in.", P(3.5), "And out.", P(5),
            "The day is done. Rest well.",
        ),
    ),
    Session(
        slug='awake-in-the-night',
        title='Awake in the night',
        category='sleep',
        description="For when you wake in the small hours and can't get back to sleep, or your mind won't stop. Quiet and slow. About 7 minutes.",
        free=False,
        parts=(
            "If you're awake in the middle of the night, that's okay. Lots of people are, "
            "especially early in recovery. Sleep often takes a while to settle.", P(4),
            "If a craving woke you, or the night feels like too much, there are free craving tools "
            "in the audio library, and if you're in danger, you can call or text 9 8 8.", P(4),
            "Don't reach for the clock. The time doesn't matter right now.", P(4),
            "Let yourself lie still, and take a slow breath in.", P(4),
            "And out, longer than the in breath.", P(8),
            "Again. In.", P(4), "And slowly out.", P(9),
            "You don't have to fall asleep. Just resting in the dark, quiet and still, is still "
            "rest. Your body is still recovering.", P(10),
            "If your mind is busy, that's normal at night. Worries feel bigger in the dark "
            "than they will in the morning.", P(6),
            "Let's give your mind something gentle to hold instead. Count your breaths out, "
            "from one up to ten. If you lose count, just start again at one. "
            "There's no way to get this wrong.", P(30),
            "Keep counting, slowly.", P(30),
            "Now let the counting go, and notice the weight of your body. Your head on the pillow.", P(10),
            "Your arms, resting.", P(10), "Your legs, heavy.", P(10),
            "Feel the bed holding all of you. You don't have to hold yourself up.", P(14),
            "If a thought pulls you back, notice it, and say to yourself, morning. That's for "
            "the morning. Then come back to your breath.", P(15),
            "Breathe in.", P(4), "And out.", P(10),
            "Picture something slow and steady. Waves on a shore. Rain on a window. "
            "Snow falling with no sound.", P(20),
            "Stay with it.", P(25),
            "Breathe in.", P(4), "And out.", P(12),
            "You can let my voice go now. Rest here as long as you like.", P(25),
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
