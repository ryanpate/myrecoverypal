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
    # --- Cravings passing ---
    {
        "quote": "A craving is a wave — it rises, peaks, and breaks, whether or not you fight it.",
        "prompt": "What does it feel like in your body when a craving finally breaks?",
    },
    {
        "quote": "The urge that feels unbearable at eight o'clock is often unrecognizable by a quarter past.",
        "prompt": "Can you commit to just fifteen more minutes right now?",
    },
    {
        "quote": "You don't have to win the argument with a craving. You just have to not answer the phone.",
        "prompt": "What's one way you can let a craving ring out today instead of picking up?",
    },
    {
        "quote": "Cravings ask for forever. All you owe them is the next five minutes.",
        "prompt": "What would the next five minutes look like if you stopped negotiating?",
    },
    {
        "quote": "The craving is not a verdict on your recovery. It's weather passing through.",
        "prompt": "What forecast would you give today's craving, and what comes after the storm?",
    },
    {
        "quote": "Naming a craving out loud takes some of its power away.",
        "prompt": "Who could you tell about this craving before it gets bigger in your head?",
    },
    {
        "quote": "Urges lie about how long they'll last. Every single one has ended before.",
        "prompt": "Think of the last craving you outlasted. How long did it actually take?",
    },
    {
        "quote": "You are not your craving. You are the one who noticed it.",
        "prompt": "What part of you stayed calm enough to notice the craving happening?",
    },
    {
        "quote": "A craving wants a decision right now. Delay is not the same as defeat.",
        "prompt": "What's one way you can buy yourself twenty more minutes today?",
    },
    {
        "quote": "The itch to use is not a command. It's an old habit talking louder than it should.",
        "prompt": "What would it sound like if you talked back to that old habit?",
    },
    {
        "quote": "Every craving you've already survived is proof the next one is survivable too.",
        "prompt": "How many cravings have you already outlasted without realizing it?",
    },
    # --- Self-compassion after setbacks ---
    {
        "quote": "A slip is information, not identity.",
        "prompt": "What is the setback trying to teach you, separate from what it says about your worth?",
    },
    {
        "quote": "Beating yourself up for longer than the mistake lasted is its own kind of relapse.",
        "prompt": "How long are you willing to let this mistake keep hurting you?",
    },
    {
        "quote": "You can regret what happened and still refuse to be cruel to yourself about it.",
        "prompt": "What would it sound like to tell yourself the truth without contempt?",
    },
    {
        "quote": "The version of you that stumbled is the same version capable of standing back up today.",
        "prompt": "What's the next right action, regardless of yesterday?",
    },
    {
        "quote": "Shame says quit. Accountability says continue, honestly.",
        "prompt": "Which voice are you listening to right now?",
    },
    {
        "quote": "A bad day does not erase a good year.",
        "prompt": "What progress from this year is still true, even today?",
    },
    {
        "quote": "Forgiving yourself is not letting yourself off the hook. It's taking the hook out so you can keep fishing.",
        "prompt": "What would change if you forgave yourself for this one thing today?",
    },
    {
        "quote": "You would not abandon a friend for struggling. Don't abandon yourself either.",
        "prompt": "What would you say to a friend in your exact situation right now?",
    },
    {
        "quote": "Setbacks are part of the shape of recovery, not proof it failed.",
        "prompt": "How does this setback fit into the larger shape of your progress?",
    },
    {
        "quote": "The kindest thing you can do after a hard fall is get back up gently, not violently.",
        "prompt": "What would a gentle return to your routine look like today?",
    },
    {
        "quote": "Self-compassion is not softness. It's the discipline of staying in the fight without adding more wounds.",
        "prompt": "Where could you replace self-criticism with something closer to discipline?",
    },
    # --- One day at a time / patience with the process ---
    {
        "quote": "You don't have to solve your whole life today. You have to get through today.",
        "prompt": "What does 'just today' look like if you strip away tomorrow's worries?",
    },
    {
        "quote": "Healing runs on its own clock, and that clock does not owe you an explanation.",
        "prompt": "Where are you demanding a timeline that healing hasn't agreed to?",
    },
    {
        "quote": "Slow change is still change. It just doesn't announce itself.",
        "prompt": "What change in yourself has been too slow to notice until now?",
    },
    {
        "quote": "The point is not to arrive quickly. The point is to still be walking next year.",
        "prompt": "What pace would you need to walk at to still be walking a year from now?",
    },
    {
        "quote": "Some days recovery looks like courage. Other days it just looks like showing up.",
        "prompt": "What does today's recovery actually look like, without judging it?",
    },
    {
        "quote": "You are allowed to measure progress in weeks instead of hours.",
        "prompt": "What does this week look like compared to last week?",
    },
    {
        "quote": "Patience is not passive. It's the active choice to keep going without rushing the outcome.",
        "prompt": "Where is impatience costing you more than it's helping?",
    },
    {
        "quote": "Today is not a test you can fail permanently. It's one square in a very long calendar.",
        "prompt": "How would you treat today differently if you knew tomorrow was a fresh square?",
    },
    {
        "quote": "The process doesn't need you to trust it completely. It just needs you to keep participating.",
        "prompt": "What's one way you can participate in your own process today, trust or not?",
    },
    {
        "quote": "Growth that happens too fast rarely holds. Slow is often how it stays.",
        "prompt": "What part of your recovery has taken longer than expected, and held better because of it?",
    },
    {
        "quote": "You are not behind. There is no schedule everyone else is on that you're missing.",
        "prompt": "Whose timeline are you comparing yourself to, and does it actually apply to you?",
    },
    # --- Connection / asking for help ---
    {
        "quote": "Asking for help is not the emergency exit from independence. It's the door back into connection.",
        "prompt": "What's one thing you're carrying alone that you could hand to someone else today?",
    },
    {
        "quote": "You were never meant to do recovery as a solo project.",
        "prompt": "Who is on your team, and have you actually let them in this week?",
    },
    {
        "quote": "A short text that says 'having a hard day' can do more than an hour of white-knuckling alone.",
        "prompt": "Who could you send that text to right now?",
    },
    {
        "quote": "The people who love you would rather be interrupted than find out too late.",
        "prompt": "What are you not telling someone because you don't want to interrupt them?",
    },
    {
        "quote": "Isolation feels like protection and works like erosion.",
        "prompt": "What connection have you been quietly letting erode?",
    },
    {
        "quote": "Community doesn't require you to have it all figured out first.",
        "prompt": "What would it look like to show up unfinished today?",
    },
    {
        "quote": "Reaching out is not weakness with better PR. It's actual strength.",
        "prompt": "What story about asking for help are you ready to stop believing?",
    },
    {
        "quote": "You don't have to earn support by being further along. You qualify by being here.",
        "prompt": "What permission are you waiting for before you let someone help you?",
    },
    {
        "quote": "Two people carrying a weight together will always outlast one person carrying it alone.",
        "prompt": "What weight could you set down by simply naming it to someone else?",
    },
    {
        "quote": "The bravest sentence in recovery is often just, 'I need to talk.'",
        "prompt": "Is there a version of that sentence you've been putting off saying?",
    },
    {
        "quote": "Being known, fully, is safer than being impressive.",
        "prompt": "Who in your life actually knows what today has been like for you?",
    },
    # --- Gratitude ---
    {
        "quote": "Gratitude doesn't require good circumstances. It only requires attention.",
        "prompt": "What have you paid enough attention to today to actually be grateful for?",
    },
    {
        "quote": "Noticing one good thing does not mean pretending the hard things aren't real.",
        "prompt": "What hard thing and what good thing are both true for you right now?",
    },
    {
        "quote": "A grateful list of three things can outweigh a mental list of thirty complaints.",
        "prompt": "What are three specific things, however small, you're grateful for today?",
    },
    {
        "quote": "The body that carried you through your worst days is still carrying you now. That's worth noticing.",
        "prompt": "What has your body done for you today that you haven't thanked it for?",
    },
    {
        "quote": "Gratitude turns what you have into enough.",
        "prompt": "What do you already have that would feel like plenty if you stopped comparing it?",
    },
    {
        "quote": "You can be thankful for how far you've come without pretending the road is finished.",
        "prompt": "How far have you actually come, measured honestly?",
    },
    {
        "quote": "Some of the smallest things, like a working car or a full night's sleep, were once the hardest things to get back.",
        "prompt": "What ordinary thing in your life used to feel impossible?",
    },
    {
        "quote": "Gratitude is a muscle. It gets stronger the more often you use it, even on hard days.",
        "prompt": "What's one rep of gratitude you can do right now, even if it's difficult?",
    },
    {
        "quote": "Looking for what's still good is not denial. It's balance.",
        "prompt": "What good thing is easy to overlook today because a hard thing is louder?",
    },
    {
        "quote": "The people who showed up for you deserve more than silent appreciation.",
        "prompt": "Who could you actually thank out loud today?",
    },
    {
        "quote": "You don't have to wait for a milestone to feel thankful for where you are.",
        "prompt": "What ordinary detail of today deserves your gratitude?",
    },
    # --- Identity change ---
    {
        "quote": "You are not the worst thing you've ever done. You are also the person choosing differently today.",
        "prompt": "What choice today reflects who you're becoming, not who you were?",
    },
    {
        "quote": "Recovery is not about becoming someone else. It's about becoming who you were before the noise got loud.",
        "prompt": "What part of yourself feels like it's returning rather than being invented?",
    },
    {
        "quote": "Identity is built in repetitions, not declarations.",
        "prompt": "What small repeated action is quietly building the person you want to be?",
    },
    {
        "quote": "You get to decide what your story means, not just what happened in it.",
        "prompt": "What meaning are you choosing to give your story today?",
    },
    {
        "quote": "The label someone gave you years ago does not get a vote in who you are now.",
        "prompt": "What old label are you ready to stop carrying?",
    },
    {
        "quote": "You are allowed to outgrow the reputation you used to have.",
        "prompt": "Where in your life is your reputation lagging behind your actual growth?",
    },
    {
        "quote": "Becoming a new version of yourself doesn't erase the old one. It just stops letting the old one drive.",
        "prompt": "What would it look like to let today's version of you take the wheel?",
    },
    {
        "quote": "You're not pretending to be different. The evidence is in what you do each day.",
        "prompt": "What evidence did you add to your own case today?",
    },
    {
        "quote": "Who you are is decided far more by ordinary afternoons than by any single dramatic moment.",
        "prompt": "What did this ordinary afternoon say about who you're becoming?",
    },
    {
        "quote": "The person you're becoming doesn't need the old one's permission.",
        "prompt": "What would you do today if you stopped asking your old self for approval?",
    },
    # --- HALT: hungry, angry, lonely, tired / boredom / stress ---
    {
        "quote": "Hungry, angry, lonely, tired: check the simple things before you trust the big feelings.",
        "prompt": "Which of the four are actually driving how you feel right now?",
    },
    {
        "quote": "Boredom is not an emergency. It just feels like one when you're used to constant stimulation.",
        "prompt": "What would it feel like to sit with boredom for five more minutes than usual?",
    },
    {
        "quote": "Stress narrows your options until everything looks like an emergency exit.",
        "prompt": "What's one option stress is hiding from you right now?",
    },
    {
        "quote": "A body that hasn't eaten or slept will lie to you about how you're doing emotionally.",
        "prompt": "Have you actually eaten, rested, or moved today?",
    },
    {
        "quote": "Anger is often a messenger for something more vulnerable underneath.",
        "prompt": "What's underneath the anger you're feeling right now?",
    },
    {
        "quote": "Restlessness is not a signal to escape. Sometimes it's just energy asking for a direction.",
        "prompt": "Where could you point this restless energy instead of running from it?",
    },
    {
        "quote": "Loneliness in a crowd is still loneliness. It's not about how many people are around you.",
        "prompt": "When did you last feel truly connected, even briefly?",
    },
    {
        "quote": "The hardest hour of the day deserves a plan, not just willpower.",
        "prompt": "What's your plan for your hardest hour today?",
    },
    {
        "quote": "Tiredness makes small problems look unsolvable. Sleep first, decide later.",
        "prompt": "What decision could wait until after you've rested?",
    },
    {
        "quote": "Empty time isn't dangerous by itself. What you fill it with is what matters.",
        "prompt": "What's one thing you could fill an empty hour with today?",
    },
    {
        "quote": "Stress shrinks your patience before it touches anything else.",
        "prompt": "Where has your patience already worn thin today, and why?",
    },
    {
        "quote": "You can be overwhelmed and still only need to handle the next five minutes.",
        "prompt": "What is the very next five-minute task in front of you?",
    },
    {
        "quote": "A racing mind slows down when the body finally moves.",
        "prompt": "What's one physical movement that could interrupt a racing mind right now?",
    },
    {
        "quote": "The urge to numb out often shows up right when a feeling gets too specific to ignore.",
        "prompt": "What feeling got specific right before you wanted to numb it?",
    },
    {
        "quote": "Irritability is often exhaustion wearing a different mask.",
        "prompt": "What are you actually exhausted from underneath the irritation?",
    },
    {
        "quote": "Naming the discomfort, bored, anxious, restless, shrinks it down to something you can work with.",
        "prompt": "What's the exact word for what you're feeling right now?",
    },
    # --- Celebrating small wins ---
    {
        "quote": "A win doesn't have to be loud to count.",
        "prompt": "What quiet win happened today that deserves acknowledgment?",
    },
    {
        "quote": "You made it through today. That is not a small thing, even on a day that felt small.",
        "prompt": "What did making it through today actually require of you?",
    },
    {
        "quote": "Celebrate the version of the win nobody else would notice.",
        "prompt": "What did you do today that only you would recognize as progress?",
    },
    {
        "quote": "Small wins compound. They just don't announce it while they're happening.",
        "prompt": "What small win from a month ago is still paying off today?",
    },
    {
        "quote": "You don't need a milestone to deserve a moment of pride.",
        "prompt": "What ordinary moment today deserves a little pride?",
    },
    {
        "quote": "Getting out of bed on the hard days is its own category of victory.",
        "prompt": "What did it take for you to start today?",
    },
    {
        "quote": "A streak is just a series of small decisions nobody applauded in the moment.",
        "prompt": "What decision today is quietly extending a streak you're proud of?",
    },
    {
        "quote": "Notice what you didn't do today, too. Sometimes restraint is the whole win.",
        "prompt": "What did you choose not to do today that matters?",
    },
    {
        "quote": "You are allowed to be proud of something small without waiting for it to become something big.",
        "prompt": "What small thing are you proud of right now, unapologetically?",
    },
    {
        "quote": "Progress hides in the things that stopped being hard.",
        "prompt": "What used to be difficult that isn't anymore?",
    },
    {
        "quote": "Every day you show up on purpose is a day that adds to the total.",
        "prompt": "What did showing up on purpose look like for you today?",
    },
    {
        "quote": "The absence of a crisis today is not nothing. It's what steady looks like.",
        "prompt": "What does an uneventful day tell you about how far you've come?",
    },
    {
        "quote": "You don't have to wait until the end of the journey to mark the miles you've already walked.",
        "prompt": "How many miles have you already walked that you haven't given yourself credit for?",
    },
    {
        "quote": "A single kept promise to yourself is worth pausing to notice.",
        "prompt": "What promise to yourself did you keep today?",
    },
    {
        "quote": "Fall seven times, stand up eight.",
        "author": "Japanese Proverb",
        "prompt": "Which 'eighth time' are you on right now, and what does standing up look like today?",
    },
    {
        "quote": "Nobody sees most of your hardest moments. Acknowledge them yourself.",
        "prompt": "What hard moment today deserves your own recognition, even if no one else saw it?",
    },
    # --- Honesty ---
    {
        "quote": "Honesty with yourself is the maintenance work nobody sees but everybody benefits from.",
        "prompt": "What truth about yourself have you been avoiding maintenance on?",
    },
    {
        "quote": "A small lie to keep the peace usually costs more peace than it saves.",
        "prompt": "Where have you traded honesty for temporary comfort?",
    },
    {
        "quote": "You can't fix what you won't admit is broken.",
        "prompt": "What are you ready to stop minimizing?",
    },
    {
        "quote": "Honesty doesn't require confession to everyone. It requires no longer lying to yourself.",
        "prompt": "What have you been telling yourself that isn't true?",
    },
    {
        "quote": "Being truthful about a hard day is not the same as failing at recovery.",
        "prompt": "What would it sound like to describe today honestly, without softening it?",
    },
    {
        "quote": "Secrets take more energy to keep than the truth ever costs to tell.",
        "prompt": "What secret is quietly draining your energy right now?",
    },
    {
        "quote": "Integrity is doing the honest thing even when the dishonest one would go unnoticed.",
        "prompt": "Where did you choose honesty today when no one would have known otherwise?",
    },
    {
        "quote": "The truth you're avoiding is usually smaller than the fear of saying it.",
        "prompt": "What's the actual size of the truth you've been avoiding?",
    },
    {
        "quote": "Self-honesty starts with dropping the performance, even just for yourself.",
        "prompt": "Where are you still performing for an audience of one, yourself?",
    },
    {
        "quote": "You don't have to be ready to change something to be honest that it needs to change.",
        "prompt": "What needs honesty before it can get your readiness?",
    },
    {
        "quote": "A little discomfort now is the price of not needing bigger honesty later.",
        "prompt": "What small honest conversation could you have today instead of a harder one later?",
    },
    {
        "quote": "Trust rebuilds one honest sentence at a time.",
        "prompt": "What honest sentence could you add to the rebuild today?",
    },
    {
        "quote": "Honesty about limits is not weakness. It's the beginning of a plan that actually works.",
        "prompt": "What limit have you been dishonest with yourself about?",
    },
    {
        "quote": "The relief after telling the truth is usually bigger than the fear before it.",
        "prompt": "What truth, once told, might bring more relief than you expect?",
    },
    {
        "quote": "You can't build trust with anyone, including yourself, on a foundation of convenient half-truths.",
        "prompt": "Where have you been settling for a half-truth instead of the whole one?",
    },
    {
        "quote": "Owning a mistake out loud costs less than carrying it silently.",
        "prompt": "What mistake would cost you less to admit than to keep hiding?",
    },
    # --- Routines / sleep / health ---
    {
        "quote": "A bedtime is not childish. It's one of the most protective habits an adult can keep.",
        "prompt": "What would going to bed twenty minutes earlier do for tomorrow's version of you?",
    },
    {
        "quote": "Your body remembers every hard day you got through. It is still on your side.",
        "prompt": "What is your body asking for that you've been ignoring?",
    },
    {
        "quote": "A predictable morning gives an unpredictable day something to hold onto.",
        "prompt": "What's one anchor in your morning routine you can protect today?",
    },
    {
        "quote": "Sleep is not a luxury you earn after everything else is handled. It's what makes handling everything else possible.",
        "prompt": "How did last night's sleep shape today?",
    },
    {
        "quote": "Movement doesn't have to be intense to count. It just has to happen.",
        "prompt": "What's the smallest form of movement you could do today?",
    },
    {
        "quote": "Eating regularly is not vanity. It's mood management with a fork.",
        "prompt": "When did you last eat something that actually nourished you?",
    },
    {
        "quote": "A cluttered space can quietly become a cluttered mind.",
        "prompt": "What small area could you tidy today to clear some mental space?",
    },
    {
        "quote": "Routine is not a cage. It's scaffolding for the days you don't feel strong.",
        "prompt": "What routine is holding you up on a day you don't feel strong?",
    },
    {
        "quote": "Water, food, sunlight, sleep: the basics are basic because they work.",
        "prompt": "Which basic need have you skipped today without realizing it?",
    },
    {
        "quote": "Your nervous system remembers structure even when your mood forgets it helps.",
        "prompt": "What structure could you return to today, even without motivation?",
    },
    {
        "quote": "A short walk can do what an hour of overthinking cannot.",
        "prompt": "Could a walk answer the question you've been sitting with?",
    },
    {
        "quote": "The best time to plant a tree was twenty years ago. The second best time is now.",
        "author": "Chinese Proverb",
        "prompt": "What have you been putting off that you could plant today instead of waiting for the right time?",
    },
    {
        "quote": "The evening routine you choose tonight is a message to tomorrow morning's version of you.",
        "prompt": "What message are you sending tomorrow's you tonight?",
    },
    {
        "quote": "Rest is productive. It's just productive on a schedule nobody can see.",
        "prompt": "What is rest producing for you today that isn't visible yet?",
    },
    {
        "quote": "A body that's cared for has more room to hold difficult emotions without breaking.",
        "prompt": "How well have you cared for your body this week?",
    },
    {
        "quote": "Consistency in small habits is quieter than willpower, and it lasts longer.",
        "prompt": "What small habit have you kept consistently, even without noticing?",
    },
    # --- Helping others ---
    {
        "quote": "Helping someone else through a hard hour can steady your own.",
        "prompt": "Who could use five minutes of your attention today?",
    },
    {
        "quote": "You don't need years of recovery to be useful to someone earlier in theirs.",
        "prompt": "What do you know now that would have helped you a year ago? Who needs to hear it?",
    },
    {
        "quote": "Showing up for someone else is its own form of practicing recovery.",
        "prompt": "What would showing up for someone else look like today?",
    },
    {
        "quote": "The support you give often comes back around when you least expect to need it.",
        "prompt": "What support have you given that you didn't realize would matter later?",
    },
    {
        "quote": "Listening without fixing is sometimes the most useful thing you can offer.",
        "prompt": "Who needs you to just listen today, not solve anything?",
    },
    {
        "quote": "Being someone's steady person is a quiet kind of purpose.",
        "prompt": "Who considers you their steady person, and have you checked in with them lately?",
    },
    {
        "quote": "You can't pour from an empty cup, but a half-full one still has something to give.",
        "prompt": "What small thing could you offer someone today without depleting yourself?",
    },
    {
        "quote": "Every person who ever helped you started somewhere ordinary too.",
        "prompt": "Whose ordinary help changed the course of your day, or your year?",
    },
    {
        "quote": "Encouragement costs you almost nothing and can change someone's entire day.",
        "prompt": "Who could use a sentence of encouragement from you right now?",
    },
    {
        "quote": "Community gets stronger every time someone shows up for someone else.",
        "prompt": "How did you strengthen your community today, even in a small way?",
    },
    {
        "quote": "You don't have to have it all figured out to be a good example to someone watching.",
        "prompt": "Who might be watching how you handle today, whether you realize it or not?",
    },
    {
        "quote": "Generosity in recovery isn't about money. It's about time, patience, and presence.",
        "prompt": "What's one form of generosity you could offer today besides money?",
    },
    {
        "quote": "Helping someone else remember their worth can remind you of your own.",
        "prompt": "Whose worth could you reflect back to them today?",
    },
    {
        "quote": "A phone call that says 'just checking on you' can interrupt someone's worst day.",
        "prompt": "Who haven't you checked on in a while?",
    },
    {
        "quote": "You are someone's proof that it's possible. Live like you know that.",
        "prompt": "Who might need to see you keep going today, even from a distance?",
    },
    {
        "quote": "Service doesn't require a title. It just requires showing up.",
        "prompt": "What's one way you can show up for someone else today, no title required?",
    },
    # --- Hope ---
    {
        "quote": "Hope doesn't require certainty. It just requires a reason to keep showing up.",
        "prompt": "What's your reason to keep showing up today?",
    },
    {
        "quote": "The fact that things have gotten better before is evidence, not just a feeling.",
        "prompt": "What evidence from your own life supports hope today?",
    },
    {
        "quote": "Hope is not naive. It's the decision to keep building even when the outcome isn't guaranteed.",
        "prompt": "What are you building today, guarantee or not?",
    },
    {
        "quote": "A hard season does not cancel the good one that's coming.",
        "prompt": "What good season have you lived through a hard one to reach before?",
    },
    {
        "quote": "You don't need to see the whole path to trust that the next step exists.",
        "prompt": "What's the next visible step, even if the rest is unclear?",
    },
    {
        "quote": "Hope grows in the same place discipline does: in the daily, unremarkable choices.",
        "prompt": "What unremarkable choice today is quietly growing your hope?",
    },
    {
        "quote": "The version of your life that feels impossible right now has been built one ordinary day at a time by other people just like you.",
        "prompt": "What ordinary day could start building that life today?",
    },
    {
        "quote": "Even a small amount of hope can outlast a large amount of doubt, if you keep feeding it.",
        "prompt": "What's feeding your hope right now, and what's feeding your doubt?",
    },
    {
        "quote": "You have survived one hundred percent of your worst days so far.",
        "prompt": "What does that track record tell you about today?",
    },
    {
        "quote": "Hope is quieter than despair, so you have to listen for it on purpose.",
        "prompt": "Where do you have to listen harder today to hear hope?",
    },
    {
        "quote": "Tomorrow doesn't know yet how today turns out. Neither do you. That's room for hope.",
        "prompt": "What's still undecided about today that hope could fill?",
    },
    {
        "quote": "The people who made it through what you're going through are proof, not exceptions.",
        "prompt": "Whose story of making it through gives you hope right now?",
    },
    # --- Courage / fear ---
    {
        "quote": "Courage in recovery rarely looks dramatic. It looks like doing the uncomfortable thing anyway.",
        "prompt": "What uncomfortable thing could you do today anyway?",
    },
    {
        "quote": "Fear shrinks the moment you stop running from it and start looking straight at it.",
        "prompt": "What fear gets smaller the moment you actually name it?",
    },
    {
        "quote": "You don't have to feel brave to act brave. Action can come first.",
        "prompt": "What action could you take today before the confidence arrives?",
    },
    {
        "quote": "The bravest thing some days is simply staying.",
        "prompt": "What has staying required of you today?",
    },
    {
        "quote": "Fear of failing again is not the same as failing again.",
        "prompt": "Where are you letting the fear of a repeat outcome stop you from trying at all?",
    },
    {
        "quote": "Every uncomfortable conversation you've survived proves the next one is survivable too.",
        "prompt": "What hard conversation have you already survived that gives you evidence now?",
    },
    {
        "quote": "Courage is doing the next right thing while your hands are still shaking.",
        "prompt": "What's the next right thing, shaking hands and all?",
    },
    {
        "quote": "The thing you're avoiding usually costs less than the anxiety of avoiding it.",
        "prompt": "What's one thing you're avoiding that's actually smaller than the dread around it?",
    },
    {
        "quote": "You can be scared and still move forward. Those two things share space all the time.",
        "prompt": "What forward step could you take today while still feeling scared?",
    },
    {
        "quote": "Facing something head-on takes less energy in the long run than circling it forever.",
        "prompt": "What have you been circling instead of facing?",
    },
    {
        "quote": "New starts are unfamiliar by definition. Unfamiliar is not the same as unsafe.",
        "prompt": "What unfamiliar step feels unsafe but probably isn't?",
    },
    {
        "quote": "Bravery is a decision made fresh each time, not a trait you either have or don't.",
        "prompt": "What decision toward bravery are you making again today?",
    },
    # --- Forgiveness ---
    {
        "quote": "Forgiving someone doesn't mean reopening the door they walked through.",
        "prompt": "Whose forgiveness could you offer without inviting them back in?",
    },
    {
        "quote": "Holding a grudge keeps you tethered to the very thing you're trying to move past.",
        "prompt": "What grudge is keeping you tied to your own past?",
    },
    {
        "quote": "You can release resentment without releasing your boundaries.",
        "prompt": "What boundary can stay firm even as you let go of resentment?",
    },
    {
        "quote": "Forgiveness is a decision you might have to make more than once about the same thing.",
        "prompt": "What have you forgiven before that you need to forgive again today?",
    },
    {
        "quote": "The apology you never got doesn't have to be the reason you stay stuck.",
        "prompt": "What closure could you give yourself that someone else never offered?",
    },
    {
        "quote": "Making amends is not about being forgiven. It's about becoming someone who tries.",
        "prompt": "What amends could you make today, regardless of the outcome?",
    },
    {
        "quote": "You are allowed to forgive yourself before you've fully made up for anything.",
        "prompt": "What are you withholding forgiveness from yourself until you 'earn' it?",
    },
    {
        "quote": "Some relationships heal. Others just teach you what you needed to learn to move forward.",
        "prompt": "What has a difficult relationship taught you, even without reconciliation?",
    },
    {
        "quote": "When there is no enemy within, the enemies outside cannot hurt you.",
        "author": "African Proverb",
        "prompt": "What inner enemy, resentment, fear, or shame, are you working to disarm today?",
    },
    {
        "quote": "You don't owe anyone access to you as proof that you've forgiven them.",
        "prompt": "What does your forgiveness actually require, separate from what others expect?",
    },
    {
        "quote": "Making peace with the past doesn't mean agreeing that it was okay.",
        "prompt": "What peace could you make with your past without excusing it?",
    },
    {
        "quote": "The people who hurt you don't get to also keep your future.",
        "prompt": "What piece of your future are you reclaiming from an old hurt today?",
    },
    # --- Purpose / meaning ---
    {
        "quote": "Meaning doesn't always arrive as a grand plan. Sometimes it shows up as the next useful thing to do.",
        "prompt": "What's the next useful thing in front of you?",
    },
    {
        "quote": "A purpose doesn't have to be permanent to be real right now.",
        "prompt": "What feels purposeful for you today, even if it changes later?",
    },
    {
        "quote": "You don't need the whole meaning of your life figured out to find meaning in today.",
        "prompt": "What made today matter, even a little?",
    },
    {
        "quote": "What you went through can become the thing that helps someone else through it too.",
        "prompt": "What part of your story might one day help someone else?",
    },
    {
        "quote": "Purpose grows out of paying attention to what you actually care about, not what you think you should.",
        "prompt": "What do you actually care about, separate from what you think you're supposed to?",
    },
    {
        "quote": "A life doesn't need a headline to be meaningful. It needs a series of honest days.",
        "prompt": "What honest day could you add to that series today?",
    },
    {
        "quote": "The smallest contribution, done consistently, outlasts the grandest idea that never starts.",
        "prompt": "What small, consistent contribution could you start today?",
    },
    {
        "quote": "You are allowed to build meaning slowly, one interest and one relationship at a time.",
        "prompt": "What interest or relationship could you invest in this week?",
    },
    {
        "quote": "Recovery gave you back time. What you do with it is where the meaning lives.",
        "prompt": "What are you doing with the time recovery gave back to you?",
    },
    {
        "quote": "Feeling useful to even one person can be enough purpose for one day.",
        "prompt": "Who could you be useful to today?",
    },
    {
        "quote": "You don't have to justify why something matters to you. It's allowed to just matter.",
        "prompt": "What matters to you that you've stopped explaining or defending?",
    },
    {
        "quote": "The search for meaning gets easier once you stop waiting for it to arrive fully formed.",
        "prompt": "What partial, unfinished meaning could you accept as enough for today?",
    },
    # --- Resilience ---
    {
        "quote": "Resilience isn't never breaking. It's what you do after you already have.",
        "prompt": "What did you do after the last time you broke a little?",
    },
    {
        "quote": "You are not made of glass. You are made of whatever survives being dropped and still holds its shape.",
        "prompt": "What shape have you held onto through your hardest moments?",
    },
    {
        "quote": "Bending under pressure and breaking under pressure are not the same thing.",
        "prompt": "Where have you bent this week without breaking?",
    },
    {
        "quote": "The comeback rarely looks like the setback in reverse. It looks like something new built from the pieces.",
        "prompt": "What new thing are you building from old pieces?",
    },
    {
        "quote": "Every hard year leaves you with tools the easy years never could.",
        "prompt": "What tool did a hard season leave you with that you still use?",
    },
    {
        "quote": "Resilience is quiet. It rarely gets applause in the moment it's happening.",
        "prompt": "What quiet resilience are you practicing today that no one's clapping for?",
    },
    {
        "quote": "You've adapted to harder things than today is asking of you.",
        "prompt": "What harder thing have you already adapted to?",
    },
    {
        "quote": "Toughness and softness can live in the same person at the same time.",
        "prompt": "Where do you hold both toughness and softness today?",
    },
    {
        "quote": "The ability to keep going is built the same way muscle is: under some resistance, not none.",
        "prompt": "What resistance today is quietly building your capacity?",
    },
    {
        "quote": "You don't have to feel unbreakable to be resilient. You just have to keep choosing to continue.",
        "prompt": "What does choosing to continue look like for you today?",
    },
    {
        "quote": "Some of your strongest qualities were forged in your hardest seasons, not your easiest ones.",
        "prompt": "What strength did a hard season forge in you?",
    },
    {
        "quote": "A smooth sea never made a skilled sailor.",
        "author": "English Proverb",
        "prompt": "What skill is this rough patch quietly teaching you?",
    },
    {
        "quote": "Resilience is less about never needing rest and more about resting without quitting.",
        "prompt": "What rest do you need today that doesn't mean giving up?",
    },
    {
        "quote": "You have already proven you can survive what you thought would end you.",
        "prompt": "What did you survive that once felt like the end?",
    },
    {
        "quote": "The storm doesn't ask if you're ready. It just asks if you'll keep your footing.",
        "prompt": "What footing are you keeping steady through today's storm?",
    },
    {
        "quote": "Every scar is proof the wound closed, not just that it happened.",
        "prompt": "What scar of yours is proof of healing rather than just proof of hurt?",
    },
    # --- Boundaries / self-respect ---
    {
        "quote": "A boundary is not a wall. It's a doorway you control.",
        "prompt": "What doorway do you need to start controlling more intentionally?",
    },
    {
        "quote": "Saying no to what drains you is saying yes to what you're trying to protect.",
        "prompt": "What no could protect something important today?",
    },
    {
        "quote": "Self-respect sounds like small, consistent decisions nobody else notices.",
        "prompt": "What small decision today was really about self-respect?",
    },
    {
        "quote": "You are allowed to leave situations that no longer fit who you're becoming.",
        "prompt": "What situation have you outgrown but stayed in out of habit?",
    },
    {
        "quote": "Protecting your peace is not selfish. It's maintenance.",
        "prompt": "What peace are you due for maintaining today?",
    },
    {
        "quote": "A boundary you don't enforce is just a suggestion.",
        "prompt": "What boundary needs you to actually enforce it this week?",
    },
    {
        "quote": "You don't owe anyone access to you just because they want it.",
        "prompt": "Where have you confused someone's want for your obligation?",
    },
    {
        "quote": "Respecting yourself sometimes means disappointing someone else.",
        "prompt": "Whose disappointment are you willing to risk in order to respect yourself?",
    },
    {
        "quote": "The relationships that survive your boundaries were probably healthy to begin with.",
        "prompt": "Which relationship has gotten healthier since you set a boundary in it?",
    },
    {
        "quote": "You can care about someone and still not be available to them right now.",
        "prompt": "Where do care and unavailability need to coexist for you today?",
    },
    {
        "quote": "Guilt about a boundary usually fades faster than resentment about not having one.",
        "prompt": "What boundary would trade a little guilt now for a lot of resentment later?",
    },
    {
        "quote": "Self-respect is choosing the harder short-term conversation over the easier long-term resentment.",
        "prompt": "What harder conversation would save you from a longer resentment?",
    },
    {
        "quote": "You are not required to explain a boundary to justify having it.",
        "prompt": "What boundary have you been over-explaining instead of just holding?",
    },
    {
        "quote": "Protecting your recovery sometimes means protecting your distance.",
        "prompt": "What distance is currently protecting your recovery?",
    },
    {
        "quote": "The word 'no' is a complete sentence, even to people you love.",
        "prompt": "Where could a simple no serve you better than a complicated explanation?",
    },
    {
        "quote": "You teach people how to treat you by what you're willing to repeat.",
        "prompt": "What pattern are you ready to stop repeating?",
    },
    # --- Acceptance / letting go ---
    {
        "quote": "Acceptance is not agreement. It's just no longer arguing with what already happened.",
        "prompt": "What are you still arguing with that has already happened?",
    },
    {
        "quote": "You can't pour energy into changing the past and into building the present at the same time.",
        "prompt": "Where is energy going toward the unchangeable instead of the possible?",
    },
    {
        "quote": "Letting go doesn't mean it didn't matter. It means it doesn't get to run today anymore.",
        "prompt": "What is still running your day that you're ready to let go of?",
    },
    {
        "quote": "Some things are not yours to fix, only yours to accept.",
        "prompt": "What have you been trying to fix that was never actually yours to carry?",
    },
    {
        "quote": "Peace often starts with admitting what you cannot control, out loud.",
        "prompt": "What could you admit out loud today that you can't control?",
    },
    {
        "quote": "Acceptance frees up the energy that resistance was quietly spending.",
        "prompt": "What would you do with the energy resistance is currently using up?",
    },
    {
        "quote": "You can mourn what didn't happen and still move forward into what will.",
        "prompt": "What unfulfilled hope are you allowed to grieve today?",
    },
    {
        "quote": "Not every chapter gets a satisfying ending. Some just end.",
        "prompt": "What unfinished chapter are you ready to close without a neat resolution?",
    },
    {
        "quote": "Letting go of who you thought you'd be by now makes room for who you actually are.",
        "prompt": "What expectation of yourself are you ready to release?",
    },
    {
        "quote": "You don't have to like a situation to stop fighting reality about it.",
        "prompt": "What reality could you stop fighting, even if you still dislike it?",
    },
    {
        "quote": "Some doors close because they were never meant to be walked through twice.",
        "prompt": "What closed door are you finally ready to stop knocking on?",
    },
    {
        "quote": "Surrender in recovery isn't giving up. It's putting down what was never yours to hold.",
        "prompt": "What have you been holding that was never actually yours to hold?",
    },
    {
        "quote": "You can accept a hard truth today and still work to change tomorrow.",
        "prompt": "What hard truth today doesn't have to be your permanent tomorrow?",
    },
    {
        "quote": "Trying to control an outcome you have no power over is exhausting in a very specific way.",
        "prompt": "What outcome are you exhausting yourself trying to control?",
    },
    {
        "quote": "Little by little, one travels far.",
        "author": "Peruvian Proverb",
        "prompt": "What far-off goal are you reaching through today's little bit?",
    },
    {
        "quote": "What you resist tends to stay loud. What you accept tends to get quiet.",
        "prompt": "What might get quieter today if you finally accepted it?",
    },
    # --- Joy / humor / lightness ---
    {
        "quote": "Recovery is allowed to include laughter, even about itself.",
        "prompt": "What's something about your recovery you can finally laugh at?",
    },
    {
        "quote": "Joy is not proof that everything is fixed. It's proof that something good got through anyway.",
        "prompt": "What good got through today, unfixed circumstances and all?",
    },
    {
        "quote": "A good laugh can loosen a grip that seriousness never could.",
        "prompt": "When did you last laugh hard enough to feel it loosen something?",
    },
    {
        "quote": "You are allowed to enjoy your life while you're still healing it.",
        "prompt": "What's one thing you could enjoy today without waiting to be fully healed first?",
    },
    {
        "quote": "Lightness is not the opposite of taking recovery seriously. It's often what makes it sustainable.",
        "prompt": "Where could a little lightness make your effort more sustainable?",
    },
    {
        "quote": "Play is not a reward you earn after the hard work. It's part of what makes the hard work possible.",
        "prompt": "What playful thing have you been postponing until you 'deserve' it?",
    },
    {
        "quote": "Some of the best proof that you're healing is that ordinary things have started to feel fun again.",
        "prompt": "What used to feel like a chore that now feels like fun?",
    },
    {
        "quote": "A sense of humor about your own mistakes is not the same as not taking them seriously.",
        "prompt": "What mistake could you hold with both seriousness and a little humor?",
    },
    {
        "quote": "Delight in small things is a skill, and it comes back the more you practice noticing it.",
        "prompt": "What small delight did you notice today?",
    },
    {
        "quote": "You don't have to earn the right to feel good today.",
        "prompt": "What good feeling are you allowed to simply accept, no earning required?",
    },
    {
        "quote": "The people who laugh easily in recovery aren't in denial. They've just made room for both truths at once.",
        "prompt": "What two truths, hard and light, are both true for you today?",
    },
    {
        "quote": "Curiosity about your own life again is one of the quiet gifts of getting well.",
        "prompt": "What have you gotten curious about again since things got better?",
    },
    {
        "quote": "Silliness is underrated as a recovery tool.",
        "prompt": "What's one silly, low-stakes thing you could do today just because?",
    },
    {
        "quote": "A good memory being made today is worth just as much as one being healed from yesterday.",
        "prompt": "What good memory is today quietly becoming?",
    },
    {
        "quote": "You're allowed to be lighthearted about a life you used to think you'd never get back.",
        "prompt": "What part of your life feels light again that once felt lost?",
    },
    {
        "quote": "Fun doesn't undo the work. It's often the whole reason for it.",
        "prompt": "What fun today reminds you why the work is worth it?",
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
