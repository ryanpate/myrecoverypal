"""
Management command to seed 90+ daily recovery thoughts/quotes.

Usage:
    python manage.py seed_recovery_quotes
    python manage.py seed_recovery_quotes --start-date 2026-01-01
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.accounts.models import DailyRecoveryThought

QUOTES = [
    # --- AA / Recovery tradition ---
    {
        "quote": "One day at a time.",
        "author": "AA Tradition",
        "prompt": "What is one small thing you can do today to support your recovery?",
    },
    {
        "quote": "Easy does it.",
        "author": "AA Tradition",
        "prompt": "Where in your life are you pushing too hard right now? How can you ease up?",
    },
    {
        "quote": "Let go and let God.",
        "author": "AA Tradition",
        "prompt": "What are you holding onto that you could release today?",
    },
    {
        "quote": "Keep it simple.",
        "author": "AA Tradition",
        "prompt": "What unnecessary complexity can you remove from your day?",
    },
    {
        "quote": "This too shall pass.",
        "author": "Ancient Proverb",
        "prompt": "What difficult feeling are you experiencing today that you trust will pass?",
    },
    {
        "quote": "First things first.",
        "author": "AA Tradition",
        "prompt": "What is the single most important thing you need to tend to today?",
    },
    {
        "quote": "Live and let live.",
        "author": "AA Tradition",
        "prompt": "Where are you spending energy judging or controlling others? What would it feel like to release that?",
    },
    {
        "quote": "Progress, not perfection.",
        "author": "AA Literature",
        "prompt": "How have you grown recently, even if imperfectly?",
    },
    {
        "quote": "We are not the same persons this year as last; nor are we those we hope to be.",
        "author": "W.E.B. Du Bois",
        "prompt": "How are you different today than you were a year ago?",
    },
    {
        "quote": "The greatest glory in living lies not in never falling, but in rising every time we fall.",
        "author": "Nelson Mandela",
        "prompt": "What is the most meaningful time you have risen after falling?",
    },
    # --- Stoic philosophy ---
    {
        "quote": "You have power over your mind, not outside events. Realize this, and you will find strength.",
        "author": "Marcus Aurelius",
        "prompt": "What external event are you allowing to control your mood today? What can you actually control?",
    },
    {
        "quote": "The obstacle is the way.",
        "author": "Marcus Aurelius",
        "prompt": "What obstacle in your recovery might actually be pointing you toward growth?",
    },
    {
        "quote": "He who is brave is free.",
        "author": "Seneca",
        "prompt": "What would you do today if fear were not holding you back?",
    },
    {
        "quote": "Waste no more time arguing about what a good man should be. Be one.",
        "author": "Marcus Aurelius",
        "prompt": "What is one act of integrity you can carry out today?",
    },
    {
        "quote": "Make the best use of what is in your power, and take the rest as it happens.",
        "author": "Epictetus",
        "prompt": "What is within your power today? What are you trying to control that is not?",
    },
    {
        "quote": "It is not the man who has too little, but the man who craves more, who is poor.",
        "author": "Seneca",
        "prompt": "What do you already have that you could be more grateful for today?",
    },
    {
        "quote": "Confine yourself to the present.",
        "author": "Marcus Aurelius",
        "prompt": "How much of your mental energy today is spent in the past or the future instead of right now?",
    },
    {
        "quote": "The whole future lies in uncertainty: live immediately.",
        "author": "Seneca",
        "prompt": "What have you been postponing that you could begin today?",
    },
    {
        "quote": "No man is free who is not master of himself.",
        "author": "Epictetus",
        "prompt": "In what area of your life do you most want to develop self-mastery?",
    },
    {
        "quote": "First say to yourself what you would be; then do what you have to do.",
        "author": "Epictetus",
        "prompt": "Who do you want to become? What one action today moves you toward that person?",
    },
    # --- Mindfulness / Eastern wisdom ---
    {
        "quote": "The present moment is the only moment available to us, and it is the door to all moments.",
        "author": "Thich Nhat Hanh",
        "prompt": "When did you last feel fully present? What made that possible?",
    },
    {
        "quote": "Peace comes from within. Do not seek it without.",
        "author": "The Buddha",
        "prompt": "Where are you looking outside yourself for peace that only you can give yourself?",
    },
    {
        "quote": "In the middle of difficulty lies opportunity.",
        "author": "Albert Einstein",
        "prompt": "What opportunity might be hidden inside your current challenge?",
    },
    {
        "quote": "Holding onto anger is like drinking poison and expecting the other person to die.",
        "author": "The Buddha (attributed)",
        "prompt": "Is there a resentment you are carrying that is hurting you more than the person it is aimed at?",
    },
    {
        "quote": "You, yourself, as much as anybody in the entire universe, deserve your love and affection.",
        "author": "The Buddha (attributed)",
        "prompt": "How can you show yourself kindness and compassion today?",
    },
    {
        "quote": "Do not dwell in the past, do not dream of the future, concentrate the mind on the present moment.",
        "author": "The Buddha (attributed)",
        "prompt": "What are three things you can notice with your senses right now?",
    },
    {
        "quote": "Out beyond ideas of wrongdoing and rightdoing, there is a field. I will meet you there.",
        "author": "Rumi",
        "prompt": "Is there a relationship where you could release judgment and simply be present with the other person?",
    },
    {
        "quote": "The wound is the place where the light enters you.",
        "author": "Rumi",
        "prompt": "How has a past wound created unexpected strength or wisdom in your life?",
    },
    {
        "quote": "Yesterday I was clever, so I wanted to change the world. Today I am wise, so I am changing myself.",
        "author": "Rumi",
        "prompt": "What inner change are you working on that is more important than any external change?",
    },
    {
        "quote": "Ignore those that make you fearful and sad, that degrade you back towards disease and death.",
        "author": "Rumi",
        "prompt": "Which people or habits in your life are pulling you toward health, and which toward harm?",
    },
    # --- Ralph Waldo Emerson ---
    {
        "quote": "What lies behind us and what lies before us are tiny matters compared to what lies within us.",
        "author": "Ralph Waldo Emerson",
        "prompt": "What inner strength or resource do you have that you sometimes forget?",
    },
    {
        "quote": "Finish each day and be done with it. You have done what you could.",
        "author": "Ralph Waldo Emerson",
        "prompt": "Can you give yourself permission to call today complete and let it go?",
    },
    {
        "quote": "For every minute you are angry you lose sixty seconds of happiness.",
        "author": "Ralph Waldo Emerson",
        "prompt": "What would you do with the mental energy you currently spend on anger or resentment?",
    },
    {
        "quote": "To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment.",
        "author": "Ralph Waldo Emerson",
        "prompt": "In what area of your life are you most fully yourself?",
    },
    # --- Theodore Roosevelt ---
    {
        "quote": "Believe you can and you're halfway there.",
        "author": "Theodore Roosevelt",
        "prompt": "Where does self-doubt hold you back in recovery? What would you attempt if you believed you could succeed?",
    },
    {
        "quote": "Do what you can, with what you have, where you are.",
        "author": "Theodore Roosevelt",
        "prompt": "What resources do you already have that you could put to use today?",
    },
    # --- Mahatma Gandhi ---
    {
        "quote": "Be the change you wish to see in the world.",
        "author": "Mahatma Gandhi",
        "prompt": "What quality — patience, kindness, honesty — do you most want to see more of in others? Are you practicing it yourself?",
    },
    {
        "quote": "Strength does not come from physical capacity. It comes from an indomitable will.",
        "author": "Mahatma Gandhi",
        "prompt": "What act of willpower in your recovery are you most proud of?",
    },
    {
        "quote": "The future depends on what you do today.",
        "author": "Mahatma Gandhi",
        "prompt": "What action today will matter most to your future self?",
    },
    # --- Martin Luther King Jr. ---
    {
        "quote": "If you can't fly, then run, if you can't run then walk, if you can't walk then crawl, but whatever you do you have to keep moving forward.",
        "author": "Martin Luther King Jr.",
        "prompt": "What is the smallest step forward you can take today, even if it is only a crawl?",
    },
    {
        "quote": "We must accept finite disappointment, but never lose infinite hope.",
        "author": "Martin Luther King Jr.",
        "prompt": "What disappointment can you accept today without letting it extinguish your hope?",
    },
    {
        "quote": "Darkness cannot drive out darkness; only light can do that. Hate cannot drive out hate; only love can do that.",
        "author": "Martin Luther King Jr.",
        "prompt": "What negative pattern in your life could be replaced with something positive today?",
    },
    # --- Winston Churchill ---
    {
        "quote": "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        "author": "Winston Churchill",
        "prompt": "How does the idea that neither success nor failure is permanent change the way you see today?",
    },
    {
        "quote": "If you're going through hell, keep going.",
        "author": "Winston Churchill",
        "prompt": "What difficulty are you in the middle of right now that requires you simply to keep moving?",
    },
    # --- Viktor Frankl ---
    {
        "quote": "When we are no longer able to change a situation, we are challenged to change ourselves.",
        "author": "Viktor Frankl",
        "prompt": "What situation in your life cannot be changed, and how might you adapt to it instead?",
    },
    {
        "quote": "Between stimulus and response there is a space. In that space is our power to choose our response.",
        "author": "Viktor Frankl",
        "prompt": "Think of a recent trigger. What response would you choose if you paused before reacting?",
    },
    {
        "quote": "Everything can be taken from a man but one thing: the last of the human freedoms — to choose one's attitude in any given set of circumstances.",
        "author": "Viktor Frankl",
        "prompt": "What attitude are you choosing today, regardless of your circumstances?",
    },
    # --- Maya Angelou ---
    {
        "quote": "You may encounter many defeats, but you must not be defeated. In fact, it may be necessary to encounter the defeats, so you can know who you are.",
        "author": "Maya Angelou",
        "prompt": "What defeat have you experienced that taught you something essential about yourself?",
    },
    {
        "quote": "My mission in life is not merely to survive, but to thrive; and to do so with some passion, some compassion, some humor, and some style.",
        "author": "Maya Angelou",
        "prompt": "What does thriving — not just surviving — look like for you in recovery?",
    },
    {
        "quote": "I've learned that people will forget what you said, people will forget what you did, but people will never forget how you made them feel.",
        "author": "Maya Angelou",
        "prompt": "How do you want the people in your life to feel after spending time with you?",
    },
    # --- Helen Keller ---
    {
        "quote": "Although the world is full of suffering, it is also full of the overcoming of it.",
        "author": "Helen Keller",
        "prompt": "Where have you witnessed or experienced the overcoming of suffering?",
    },
    {
        "quote": "Optimism is the faith that leads to achievement. Nothing can be done without hope and confidence.",
        "author": "Helen Keller",
        "prompt": "What are you hopeful about in your recovery right now?",
    },
    # --- Abraham Lincoln ---
    {
        "quote": "Give me six hours to chop down a tree and I will spend the first four sharpening the axe.",
        "author": "Abraham Lincoln",
        "prompt": "What preparation or planning would make your recovery efforts more effective?",
    },
    {
        "quote": "I am not bound to win, but I am bound to be true.",
        "author": "Abraham Lincoln",
        "prompt": "What does living with integrity mean to you in your recovery today?",
    },
    # --- Henry David Thoreau ---
    {
        "quote": "Go confidently in the direction of your dreams. Live the life you have imagined.",
        "author": "Henry David Thoreau",
        "prompt": "What life are you imagining for yourself beyond addiction?",
    },
    {
        "quote": "Not until we are lost do we begin to find ourselves.",
        "author": "Henry David Thoreau",
        "prompt": "How has hitting a low point ultimately helped you find yourself?",
    },
    # --- Mark Twain ---
    {
        "quote": "The secret of getting ahead is getting started.",
        "author": "Mark Twain",
        "prompt": "What have you been waiting to start? What would it take to begin today?",
    },
    {
        "quote": "Twenty years from now you will be more disappointed by the things that you didn't do than by the ones you did do.",
        "author": "Mark Twain",
        "prompt": "What opportunity in your recovery might you regret not taking?",
    },
    # --- Ralph Waldo Emerson (additional) ---
    {
        "quote": "Nothing great was ever achieved without enthusiasm.",
        "author": "Ralph Waldo Emerson",
        "prompt": "What part of your recovery journey can you approach with more enthusiasm today?",
    },
    # --- Brene Brown ---
    {
        "quote": "Vulnerability is not winning or losing; it's having the courage to show up and be seen when we have no control over the outcome.",
        "author": "Brené Brown",
        "prompt": "Where in your recovery do you need to be more vulnerable, even without knowing how it will turn out?",
    },
    {
        "quote": "Owning our story and loving ourselves through that process is the bravest thing we'll ever do.",
        "author": "Brené Brown",
        "prompt": "What part of your story are you still ashamed of that deserves your own compassion?",
    },
    # --- C.S. Lewis ---
    {
        "quote": "You can't go back and change the beginning, but you can start where you are and change the ending.",
        "author": "C.S. Lewis",
        "prompt": "What does the ending you want to write from this point forward look like?",
    },
    {
        "quote": "Hardships often prepare ordinary people for an extraordinary destiny.",
        "author": "C.S. Lewis",
        "prompt": "How might your hardships be preparing you for something meaningful?",
    },
    # --- William James ---
    {
        "quote": "Act as if what you do makes a difference. It does.",
        "author": "William James",
        "prompt": "What small action today might make more of a difference than you realize?",
    },
    {
        "quote": "The greatest weapon against stress is our ability to choose one thought over another.",
        "author": "William James",
        "prompt": "What is one anxious or negative thought you can consciously replace today?",
    },
    # --- Albert Camus ---
    {
        "quote": "In the depths of winter I finally learned that within me there lay an invincible summer.",
        "author": "Albert Camus",
        "prompt": "What inner warmth or strength have you discovered in your darkest moments?",
    },
    # --- Khalil Gibran ---
    {
        "quote": "Your pain is the breaking of the shell that encloses your understanding.",
        "author": "Khalil Gibran",
        "prompt": "What understanding has your pain given you that you could not have gained any other way?",
    },
    {
        "quote": "Out of suffering have emerged the strongest souls; the most massive characters are seared with scars.",
        "author": "Khalil Gibran",
        "prompt": "Which of your scars has become a source of strength?",
    },
    # --- Lao Tzu / Tao Te Ching ---
    {
        "quote": "The journey of a thousand miles begins with one step.",
        "author": "Lao Tzu",
        "prompt": "What one step in recovery are you willing to take today?",
    },
    {
        "quote": "Knowing others is wisdom, knowing yourself is enlightenment.",
        "author": "Lao Tzu",
        "prompt": "What have you learned about yourself in recovery that surprises you?",
    },
    {
        "quote": "Nature does not hurry, yet everything is accomplished.",
        "author": "Lao Tzu",
        "prompt": "Where are you rushing your recovery? What would it feel like to trust the process?",
    },
    # --- Frederick Douglass ---
    {
        "quote": "If there is no struggle, there is no progress.",
        "author": "Frederick Douglass",
        "prompt": "What struggle in your life is also evidence of your growth?",
    },
    # --- Cicero ---
    {
        "quote": "Gratitude is not only the greatest of virtues, but the parent of all others.",
        "author": "Cicero",
        "prompt": "What are three things you are genuinely grateful for today?",
    },
    # --- Albert Schweitzer ---
    {
        "quote": "In everyone's life, at some time, our inner fire goes out. It is then burst into flame by an encounter with another human being.",
        "author": "Albert Schweitzer",
        "prompt": "Who in your life has helped rekindle your inner fire?",
    },
    # --- Harriet Beecher Stowe ---
    {
        "quote": "Never give up, for that is just the place and time that the tide will turn.",
        "author": "Harriet Beecher Stowe",
        "prompt": "Have you ever almost given up just before a breakthrough? What kept you going?",
    },
    # --- Wendell Berry ---
    {
        "quote": "It may be that when we no longer know what to do, we have come to our real work, and when we no longer know which way to go, we have begun our real journey.",
        "author": "Wendell Berry",
        "prompt": "What does feeling lost in your recovery tell you about where your real growth is happening?",
    },
    # --- Robert Frost ---
    {
        "quote": "The best way out is always through.",
        "author": "Robert Frost",
        "prompt": "What difficult feeling or situation are you avoiding that you need to go through instead?",
    },
    # --- Walt Whitman ---
    {
        "quote": "Keep your face always toward the sunshine, and shadows will fall behind you.",
        "author": "Walt Whitman",
        "prompt": "What positive focus could shift your perspective today?",
    },
    # --- Anne Frank ---
    {
        "quote": "How wonderful it is that nobody need wait a single moment before starting to improve the world.",
        "author": "Anne Frank",
        "prompt": "What small improvement — in yourself or for someone else — can you make right now?",
    },
    # --- Aristotle ---
    {
        "quote": "We are what we repeatedly do. Excellence, then, is not an act, but a habit.",
        "author": "Aristotle",
        "prompt": "What daily habit is most supporting your recovery right now?",
    },
    {
        "quote": "Knowing yourself is the beginning of all wisdom.",
        "author": "Aristotle",
        "prompt": "What have you come to understand about yourself through the process of recovery?",
    },
    # --- Plato ---
    {
        "quote": "The first and greatest victory is to conquer yourself.",
        "author": "Plato",
        "prompt": "In what area of your life have you recently conquered a part of yourself?",
    },
    # --- Ralph Waldo Emerson (additional) ---
    {
        "quote": "The only way to have a friend is to be one.",
        "author": "Ralph Waldo Emerson",
        "prompt": "How can you show up as a better friend in your recovery community today?",
    },
    # --- Inspirational / General ---
    {
        "quote": "Rock bottom became the solid foundation on which I rebuilt my life.",
        "author": "J.K. Rowling",
        "prompt": "How has your lowest point become a starting point for something better?",
    },
    {
        "quote": "You don't have to see the whole staircase, just take the first step.",
        "author": "Martin Luther King Jr.",
        "prompt": "What is the very first step you can see in front of you right now?",
    },
    {
        "quote": "Turn your wounds into wisdom.",
        "author": "Oprah Winfrey",
        "prompt": "What wisdom have your struggles given you that you could share with someone else?",
    },
    {
        "quote": "I am not what happened to me. I am what I choose to become.",
        "author": "Carl Jung",
        "prompt": "What are you actively choosing to become, separate from your past?",
    },
    {
        "quote": "Until you make the unconscious conscious, it will direct your life and you will call it fate.",
        "author": "Carl Jung",
        "prompt": "What pattern in your life would you like to bring into the light and examine honestly?",
    },
    {
        "quote": "The cave you fear to enter holds the treasure you seek.",
        "author": "Joseph Campbell",
        "prompt": "What fear in your recovery might be guarding something valuable?",
    },
    {
        "quote": "We must be willing to let go of the life we planned so as to have the life that is waiting for us.",
        "author": "Joseph Campbell",
        "prompt": "What old plan or expectation are you still clinging to that might be keeping you from the life ahead?",
    },
    {
        "quote": "Courage is not the absence of fear, but the judgment that something else is more important than fear.",
        "author": "Ambrose Redmoon",
        "prompt": "What do you value more than your fear? Let that guide you today.",
    },
    {
        "quote": "In three words I can sum up everything I've learned about life: it goes on.",
        "author": "Robert Frost",
        "prompt": "What are you relieved to know will simply continue and move forward?",
    },
    {
        "quote": "Life is not measured by the number of breaths we take, but by the moments that take our breath away.",
        "author": "Maya Angelou (attributed)",
        "prompt": "What moment in recovery has truly taken your breath away?",
    },
    {
        "quote": "Act well at the moment, and you have performed a good action to all eternity.",
        "author": "Johann Kaspar Lavater",
        "prompt": "What one good action could you perform right now, in this moment?",
    },
    {
        "quote": "Every day may not be good, but there is something good in every day.",
        "author": "Alice Morse Earle",
        "prompt": "What is one good thing — however small — you can find in today?",
    },
    {
        "quote": "What we think, we become.",
        "author": "The Buddha (attributed)",
        "prompt": "What thought pattern have you noticed recently, and is it one you want to keep thinking?",
    },
    {
        "quote": "Health is not valued till sickness comes.",
        "author": "Thomas Fuller",
        "prompt": "What aspect of your health — physical, mental, or spiritual — are you grateful for today?",
    },
    {
        "quote": "The man who moves a mountain begins by carrying away small stones.",
        "author": "Confucius",
        "prompt": "What large goal in recovery can you break into small stones to carry today?",
    },
    {
        "quote": "Our greatest glory is not in never falling, but in rising every time we fall.",
        "author": "Confucius",
        "prompt": "What does rising look like for you after a setback?",
    },
    {
        "quote": "Where there is no struggle, there is no strength.",
        "author": "Oprah Winfrey",
        "prompt": "What strength have you built directly because of struggle?",
    },
    {
        "quote": "You are never too old to set another goal or to dream a new dream.",
        "author": "C.S. Lewis",
        "prompt": "What new goal or dream has emerged for you in recovery?",
    },
    {
        "quote": "It always seems impossible until it's done.",
        "author": "Nelson Mandela",
        "prompt": "What felt impossible in your recovery that you have now accomplished?",
    },
    {
        "quote": "The most common form of despair is not being who you are.",
        "author": "Søren Kierkegaard",
        "prompt": "In what way are you most fully yourself in recovery?",
    },
    {
        "quote": "Happiness is when what you think, what you say, and what you do are in harmony.",
        "author": "Mahatma Gandhi",
        "prompt": "Where in your life is there alignment between your thoughts, words, and actions?",
    },
    {
        "quote": "A man who is a master of patience is master of everything else.",
        "author": "George Savile",
        "prompt": "Where in your recovery do you most need to practice patience?",
    },
    {
        "quote": "Wherever you go, go with all your heart.",
        "author": "Confucius",
        "prompt": "What would it look like to throw yourself wholeheartedly into your recovery today?",
    },
    {
        "quote": "Be not afraid of growing slowly; be afraid only of standing still.",
        "author": "Chinese Proverb",
        "prompt": "In what area of your recovery are you growing slowly but steadily?",
    },
    {
        "quote": "Even if I knew that tomorrow the world would go to pieces, I would still plant my apple tree.",
        "author": "Martin Luther",
        "prompt": "What is worth planting today regardless of what tomorrow holds?",
    },
]


class Command(BaseCommand):
    help = "Seed 90+ daily recovery thoughts into the DailyRecoveryThought model"

    def add_arguments(self, parser):
        parser.add_argument(
            "--start-date",
            type=str,
            default=None,
            help="Start date in YYYY-MM-DD format (defaults to today)",
        )

    def handle(self, *args, **options):
        if options["start_date"]:
            try:
                start_date = date.fromisoformat(options["start_date"])
            except ValueError:
                self.stderr.write(
                    self.style.ERROR(
                        f"Invalid date format: {options['start_date']}. Use YYYY-MM-DD."
                    )
                )
                return
        else:
            start_date = date.today()

        created_count = 0
        skipped_count = 0

        for i, entry in enumerate(QUOTES):
            quote_date = start_date + timedelta(days=i)
            obj, created = DailyRecoveryThought.objects.get_or_create(
                date=quote_date,
                defaults={
                    "quote": entry["quote"],
                    "author_attribution": entry.get("author", ""),
                    "reflection_prompt": entry.get("prompt", ""),
                },
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_count} quotes starting {start_date} "
                f"({skipped_count} skipped — already existed)."
            )
        )
