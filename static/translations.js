// static/translations.js

const RTL_LANGS = new Set(["ar", "fa"]);

const TRANSLATIONS = {
  tr: {
    app_title: "MySocial Panel",
    nav_home: "Ana Sayfa",
    nav_create: "Gönderi Oluştur",
    nav_scheduled: "Zamanlanmış",
    nav_drafts: "Hazırlananlar",
    nav_queue: "Kuyruk",
    nav_worker_logs: "Worker Log",
    nav_archive: "Arşiv",
    nav_accounts: "Hesaplar",

    page_prepare_title: "Gönderiyi Hazırla",
    page_prepare_desc:
      "Metni yaz, platform/format seç, medya ekle ve zamanla. Şimdi gönder, tek sefer, aralıklı veya kampanya modu kullanabilirsin.",
    label_schedule_mode: "Gönderim Modu",
    schedule_now: "Şimdi Gönder (kuyruğa al)",
    schedule_one_shot: "Tek Sefer (tarih/saat)",
    schedule_interval: "Aralıklı (dakika bazlı)",
    schedule_campaign: "Kampanya (günde N + tarih aralığı)",

    label_plan_type: "Plan Türü",
    plan_one_shot: "Tek Sefer (tarih/saat)",
    plan_weekly: "Haftanın Günleri (gün seç + saat)",
    plan_every_n_days: "Her N Günde Bir (periyod)",
    plan_bulk: "Toplu Gönderi (satır satır)",

    label_post_text: "Gönderi Metni",
    placeholder_post_text: "Metnini buraya yaz...",

    label_bulk_lines: "Toplu İçerik (Her satır 1 gönderi)",
    placeholder_bulk_lines:
      "1. satır: ilk gönderi metni\n2. satır: ikinci gönderi metni\n...",

    label_bulk_start: "Toplu Başlangıç Zamanı",
    label_bulk_interval: "Aralık (dakika)",
    helper_bulk_interval: "Örn: 60 = her saat, 1440 = her gün",

    label_hashtags: "Hashtagler",
    placeholder_hashtags: "#hedefler #mutluluk #bugün...",

    label_platforms: "Platformlar",
    label_format: "Format",
    format_normal: "Normal",
    format_short: "Short/Reels",
    format_story: "Story",

    label_media_type: "Medya Türü",
    media_mixed: "Karışık",
    media_image: "Sadece Foto",
    media_video: "Sadece Video",
    helper_media_type: "Seçime göre dosya seçici filtrelenir.",

    label_media_add: "Medya Ekle",

    label_one_shot_time: "Tek Sefer Zamanlama",
    label_interval_start: "Aralıklı Başlangıç",
    label_interval_minutes: "Aralık (dakika)",
    helper_interval_example: "Örn: 60 = saatte bir, 1440 = günde bir",
    label_campaign_start: "Kampanya Başlangıç",
    label_campaign_end_date: "Kampanya Bitiş (Tarih)",
    label_campaign_per_day: "Günde Kaç Paylaşım",
    helper_campaign_example: "Örn: 20 => yaklaşık her 72 dakikada bir paylaşım.",
    label_targets: "Hedefler (Opsiyonel: Sayfa/Grup)",
    placeholder_targets: "facebook:page:1090443410810890\nfacebook:group:1234567890\ninstagram:self",
    helper_targets_format:
      "Satır formatı: platform:tür:id (tür: page/group/self). Boş bırakırsan varsayılan hesaba paylaşır.",
    helper_media_add_multi:
      "Birden fazla dosya için tek seçimde toplu seçebilir veya tekrar tekrar ekleyebilirsin.",
    helper_no_media_selected: "Henüz medya seçilmedi.",
    helper_media_selected_count: "{count} medya seçildi.",
    helper_story_single_media: "Story için tek fotoğraf veya tek video seçebilirsin.",
    helper_normal_multi_media: "Normal/Short modunda birden fazla medya seçebilirsin.",
    helper_story_only_instagram: "Story modunda sadece Instagram aktiftir.",
    btn_ai_text: "AI ile Metin Öner",
    btn_ai_hashtag: "AI ile Hashtag Öner",
    alert_write_brief_first: "Önce gönderi metni/brief yaz.",
    alert_ai_text_error: "AI metin hatası: ",
    prompt_topic_short: "Kısa konu yaz (ör: kahve dükkanı açılışı):",
    alert_hashtag_need_topic: "Hashtag önerisi için kısa bir konu/metin gir.",
    alert_ai_hashtag_error: "AI hashtag hatası: ",

    label_weekly_days: "Haftanın Günleri",
    day_mon: "Pzt",
    day_tue: "Sal",
    day_wed: "Çar",
    day_thu: "Per",
    day_fri: "Cum",
    day_sat: "Cmt",
    day_sun: "Paz",
    label_weekly_time: "Saat",
    label_weekly_start: "Başlangıç",
    label_weekly_end: "Bitiş (opsiyonel)",

    label_every_n_days: "Her kaç günde bir?",
    label_every_time: "Saat",
    label_every_start: "Başlangıç",
    label_every_end: "Bitiş (opsiyonel)",

    btn_save_draft: "Taslak Olarak Kaydet",
    btn_submit_now: "Gönderiyi Oluştur",

    // Tasks/Drafts pages
    page_tasks_title: "Zamanlanmış Gönderiler",
    page_drafts_title: "Taslaklar",
    empty_list: "Henüz kayıt yok.",
    col_text: "Metin",
    col_platforms: "Platformlar",
    col_format: "Format",
    col_schedule: "Zaman",
    col_type: "Tip",
    type_one_shot: "Tek Sefer",
    type_weekly: "Haftalık",
    type_every: "Periyodik",
    type_bulk: "Toplu",
  },

  en: {
    app_title: "MySocial Panel",
    nav_home: "Home",
    nav_create: "Create Post",
    nav_scheduled: "Scheduled",
    nav_drafts: "Drafts",
    nav_queue: "Queue",
    nav_worker_logs: "Worker Log",
    nav_archive: "Archive",
    nav_accounts: "Accounts",

    page_prepare_title: "Prepare Post",
    page_prepare_desc:
      "Write the text, choose platform/format, add media, and schedule it. You can send now, one-time, interval, or campaign mode.",
    label_schedule_mode: "Send Mode",
    schedule_now: "Send Now (add to queue)",
    schedule_one_shot: "One-time (date/time)",
    schedule_interval: "Interval (minutes)",
    schedule_campaign: "Campaign (N per day + date range)",

    label_plan_type: "Plan Type",
    plan_one_shot: "One-time (date/time)",
    plan_weekly: "Weekly (select days + time)",
    plan_every_n_days: "Every N days (periodic)",
    plan_bulk: "Bulk (one post per line)",

    label_post_text: "Post Text",
    placeholder_post_text: "Write your text here...",

    label_bulk_lines: "Bulk Content (one post per line)",
    placeholder_bulk_lines:
      "Line 1: first post text\nLine 2: second post text\n...",

    label_bulk_start: "Bulk Start Time",
    label_bulk_interval: "Interval (minutes)",
    helper_bulk_interval: "Example: 60 = hourly, 1440 = daily",

    label_hashtags: "Hashtags",
    placeholder_hashtags: "#goals #happiness #today...",

    label_platforms: "Platforms",
    label_format: "Format",
    format_normal: "Normal",
    format_short: "Short/Reels",
    format_story: "Story",

    label_media_type: "Media Type",
    media_mixed: "Mixed",
    media_image: "Images only",
    media_video: "Videos only",
    helper_media_type: "The file picker is filtered based on your selection.",

    label_media_add: "Add Media",

    label_one_shot_time: "One-time Schedule",
    label_interval_start: "Interval Start",
    label_interval_minutes: "Interval (minutes)",
    helper_interval_example: "Example: 60 = hourly, 1440 = daily",
    label_campaign_start: "Campaign Start",
    label_campaign_end_date: "Campaign End (Date)",
    label_campaign_per_day: "Posts Per Day",
    helper_campaign_example: "Ex: 20 => about one post every 72 minutes.",
    label_targets: "Targets (Optional: Page/Group)",
    placeholder_targets: "facebook:page:1090443410810890\nfacebook:group:1234567890\ninstagram:self",
    helper_targets_format:
      "Line format: platform:type:id (type: page/group/self). If empty, shares to default account.",
    helper_media_add_multi:
      "For multiple files, you can select many at once or keep adding in repeated picks.",
    helper_no_media_selected: "No media selected yet.",
    helper_media_selected_count: "{count} media selected.",
    helper_story_single_media: "For Story, select a single photo or a single video.",
    helper_normal_multi_media: "In Normal/Short mode you can select multiple media files.",
    helper_story_only_instagram: "In Story mode, only Instagram is active.",
    btn_ai_text: "Suggest Text with AI",
    btn_ai_hashtag: "Suggest Hashtags with AI",
    alert_write_brief_first: "Write post text/brief first.",
    alert_ai_text_error: "AI text error: ",
    prompt_topic_short: "Write a short topic (e.g. coffee shop opening):",
    alert_hashtag_need_topic: "Enter a short topic/text for hashtag suggestions.",
    alert_ai_hashtag_error: "AI hashtag error: ",

    label_weekly_days: "Days of Week",
    day_mon: "Mon",
    day_tue: "Tue",
    day_wed: "Wed",
    day_thu: "Thu",
    day_fri: "Fri",
    day_sat: "Sat",
    day_sun: "Sun",
    label_weekly_time: "Time",
    label_weekly_start: "Start",
    label_weekly_end: "End (optional)",

    label_every_n_days: "Every how many days?",
    label_every_time: "Time",
    label_every_start: "Start",
    label_every_end: "End (optional)",

    btn_save_draft: "Save as Draft",
    btn_submit_now: "Create Post",

    page_tasks_title: "Scheduled Posts",
    page_drafts_title: "Drafts",
    empty_list: "No records yet.",
    col_text: "Text",
    col_platforms: "Platforms",
    col_format: "Format",
    col_schedule: "Schedule",
    col_type: "Type",
    type_one_shot: "One-time",
    type_weekly: "Weekly",
    type_every: "Periodic",
    type_bulk: "Bulk",
  },

  ar: {
    app_title: "لوحة MySocial",
    nav_home: "الرئيسية",
    nav_create: "إنشاء منشور",
    nav_scheduled: "المجدول",
    nav_drafts: "المسودات",
    nav_queue: "الطابور",
    nav_worker_logs: "سجل العامل",
    nav_archive: "الأرشيف",
    nav_accounts: "الحسابات",

    page_prepare_title: "تحضير المنشور",
    page_prepare_desc:
      "اكتب النص، اختر المنصة/الصيغة، أضف الوسائط ثم قم بالجدولة. يمكنك الجدولة مرة واحدة أو أسبوعيًا أو دوريًا أو بالجملة.",

    label_plan_type: "نوع الخطة",
    plan_one_shot: "مرة واحدة (تاريخ/وقت)",
    plan_weekly: "أيام الأسبوع (اختر الأيام + الوقت)",
    plan_every_n_days: "كل N أيام (دوري)",
    plan_bulk: "بالجملة (سطر لكل منشور)",

    label_post_text: "نص المنشور",
    placeholder_post_text: "اكتب نصك هنا...",

    label_bulk_lines: "محتوى بالجملة (منشور لكل سطر)",
    placeholder_bulk_lines:
      "السطر 1: نص المنشور الأول\nالسطر 2: نص المنشور الثاني\n...",

    label_bulk_start: "وقت بداية النشر بالجملة",
    label_bulk_interval: "الفاصل (بالدقائق)",
    helper_bulk_interval: "مثال: 60 = كل ساعة، 1440 = يوميًا",

    label_hashtags: "الوسوم",
    placeholder_hashtags: "#أهداف #سعادة #اليوم...",

    label_platforms: "المنصات",
    label_format: "الصيغة",
    format_normal: "عادي",
    format_short: "Short/Reels",
    format_story: "قصة",

    label_media_type: "نوع الوسائط",
    media_mixed: "مختلط",
    media_image: "صور فقط",
    media_video: "فيديو فقط",
    helper_media_type: "يتم فلترة اختيار الملفات حسب اختيارك.",

    label_media_add: "إضافة وسائط",
    label_one_shot_time: "جدولة مرة واحدة",

    label_weekly_days: "أيام الأسبوع",
    day_mon: "الإثنين",
    day_tue: "الثلاثاء",
    day_wed: "الأربعاء",
    day_thu: "الخميس",
    day_fri: "الجمعة",
    day_sat: "السبت",
    day_sun: "الأحد",
    label_weekly_time: "الوقت",
    label_weekly_start: "البداية",
    label_weekly_end: "النهاية (اختياري)",

    label_every_n_days: "كل كم يوم؟",
    label_every_time: "الوقت",
    label_every_start: "البداية",
    label_every_end: "النهاية (اختياري)",

    btn_save_draft: "حفظ كمسودة",
    btn_submit_now: "إنشاء المنشور",

    page_tasks_title: "المنشورات المجدولة",
    page_drafts_title: "المسودات",
    empty_list: "لا توجد سجلات بعد.",
    col_text: "النص",
    col_platforms: "المنصات",
    col_format: "الصيغة",
    col_schedule: "الجدولة",
    col_type: "النوع",
    type_one_shot: "مرة واحدة",
    type_weekly: "أسبوعي",
    type_every: "دوري",
    type_bulk: "بالجملة",
  },

  fa: {
    app_title: "پنل MySocial",
    nav_home: "خانه",
    nav_create: "ساخت پست",
    nav_scheduled: "زمان‌بندی‌شده",
    nav_drafts: "پیش‌نویس‌ها",
    nav_queue: "صف",
    nav_worker_logs: "لاگ پردازشگر",
    nav_archive: "آرشیو",
    nav_accounts: "حساب‌ها",

    page_prepare_title: "آماده‌سازی پست",
    page_prepare_desc:
      "متن را بنویس، پلتفرم/فرمت را انتخاب کن، رسانه اضافه کن و زمان‌بندی کن. حالت‌های یک‌بار، هفتگی، دوره‌ای یا گروهی.",

    label_plan_type: "نوع برنامه",
    plan_one_shot: "یک‌بار (تاریخ/زمان)",
    plan_weekly: "هفتگی (انتخاب روزها + ساعت)",
    plan_every_n_days: "هر N روز (دوره‌ای)",
    plan_bulk: "گروهی (هر خط یک پست)",

    label_post_text: "متن پست",
    placeholder_post_text: "اینجا بنویس...",

    label_bulk_lines: "محتوای گروهی (هر خط یک پست)",
    placeholder_bulk_lines:
      "خط ۱: متن پست اول\nخط ۲: متن پست دوم\n...",

    label_bulk_start: "زمان شروع گروهی",
    label_bulk_interval: "فاصله (دقیقه)",
    helper_bulk_interval: "مثال: 60 = هر ساعت، 1440 = هر روز",

    label_hashtags: "هشتگ‌ها",
    placeholder_hashtags: "#هدف #خوشحالی #امروز...",

    label_platforms: "پلتفرم‌ها",
    label_format: "فرمت",
    format_normal: "عادی",
    format_short: "Short/Reels",
    format_story: "استوری",

    label_media_type: "نوع رسانه",
    media_mixed: "ترکیبی",
    media_image: "فقط عکس",
    media_video: "فقط ویدیو",
    helper_media_type: "بر اساس انتخاب شما، فایل‌گیر فیلتر می‌شود.",

    label_media_add: "افزودن رسانه",
    label_one_shot_time: "زمان‌بندی یک‌بار",

    label_weekly_days: "روزهای هفته",
    day_mon: "دوشنبه",
    day_tue: "سه‌شنبه",
    day_wed: "چهارشنبه",
    day_thu: "پنج‌شنبه",
    day_fri: "جمعه",
    day_sat: "شنبه",
    day_sun: "یک‌شنبه",
    label_weekly_time: "ساعت",
    label_weekly_start: "شروع",
    label_weekly_end: "پایان (اختیاری)",

    label_every_n_days: "هر چند روز؟",
    label_every_time: "ساعت",
    label_every_start: "شروع",
    label_every_end: "پایان (اختیاری)",

    btn_save_draft: "ذخیره به عنوان پیش‌نویس",
    btn_submit_now: "ساخت پست",

    page_tasks_title: "پست‌های زمان‌بندی‌شده",
    page_drafts_title: "پیش‌نویس‌ها",
    empty_list: "هنوز رکوردی وجود ندارد.",
    col_text: "متن",
    col_platforms: "پلتفرم‌ها",
    col_format: "فرمت",
    col_schedule: "زمان‌بندی",
    col_type: "نوع",
    type_one_shot: "یک‌بار",
    type_weekly: "هفتگی",
    type_every: "دوره‌ای",
    type_bulk: "گروهی",
  },

  fr: {
    app_title: "MySocial Panel",
    nav_home: "Accueil",
    nav_create: "Créer",
    nav_scheduled: "Planifiés",
    nav_drafts: "Brouillons",
    nav_queue: "File d'attente",
    nav_worker_logs: "Logs worker",
    nav_archive: "Archive",
    nav_accounts: "Comptes",

    page_prepare_title: "Préparer une publication",
    page_prepare_desc:
      "Rédige le texte, choisis la plateforme/le format, ajoute un média et planifie. Tu peux envoyer maintenant, en une fois, par intervalle ou en campagne.",
    label_schedule_mode: "Mode d'envoi",
    schedule_now: "Envoyer maintenant (file d'attente)",
    schedule_one_shot: "Une fois (date/heure)",
    schedule_interval: "Intervalle (minutes)",
    schedule_campaign: "Campagne (N/jour + période)",

    label_plan_type: "Type de planification",
    plan_one_shot: "Une fois (date/heure)",
    plan_weekly: "Hebdomadaire (jours + heure)",
    plan_every_n_days: "Tous les N jours (périodique)",
    plan_bulk: "En lot (1 ligne = 1 post)",

    label_post_text: "Texte",
    placeholder_post_text: "Écris ton texte ici...",

    label_bulk_lines: "Contenu en lot (1 ligne = 1 post)",
    placeholder_bulk_lines:
      "Ligne 1 : premier post\nLigne 2 : deuxième post\n...",

    label_bulk_start: "Début (lot)",
    label_bulk_interval: "Intervalle (minutes)",
    helper_bulk_interval: "Ex: 60 = toutes les heures, 1440 = tous les jours",

    label_hashtags: "Hashtags",
    placeholder_hashtags: "#objectifs #bonheur #aujourdhui...",

    label_platforms: "Plateformes",
    label_format: "Format",
    format_normal: "Normal",
    format_short: "Short/Reels",
    format_story: "Story",

    label_media_type: "Type de média",
    media_mixed: "Mixte",
    media_image: "Images uniquement",
    media_video: "Vidéos uniquement",
    helper_media_type: "Le sélecteur de fichiers est filtré selon ton choix.",

    label_media_add: "Ajouter un média",
    label_one_shot_time: "Planification (une fois)",
    label_interval_start: "Début de l'intervalle",
    label_interval_minutes: "Intervalle (minutes)",
    helper_interval_example: "Ex: 60 = toutes les heures, 1440 = tous les jours",
    label_campaign_start: "Début de campagne",
    label_campaign_end_date: "Fin de campagne (date)",
    label_campaign_per_day: "Publications par jour",
    helper_campaign_example: "Ex: 20 => environ une publication toutes les 72 minutes.",
    label_targets: "Cibles (optionnel : page/groupe)",
    placeholder_targets: "facebook:page:1090443410810890\nfacebook:group:1234567890\ninstagram:self",
    helper_targets_format:
      "Format par ligne : plateforme:type:id (type : page/group/self). Si vide, publication vers le compte par défaut.",
    helper_media_add_multi:
      "Pour plusieurs fichiers, tu peux en sélectionner plusieurs d'un coup ou en ajouter plusieurs fois.",
    helper_no_media_selected: "Aucun média sélectionné.",
    helper_media_selected_count: "{count} média sélectionné(s).",
    helper_story_single_media: "Pour une Story, choisis une seule photo ou une seule vidéo.",
    helper_normal_multi_media:
      "En mode Normal/Short, tu peux sélectionner plusieurs médias.",
    helper_story_only_instagram: "En mode Story, seul Instagram est actif.",
    btn_ai_text: "Suggérer un texte (IA)",
    btn_ai_hashtag: "Suggérer des hashtags (IA)",
    alert_write_brief_first: "Écris d'abord le texte/brief de publication.",
    alert_ai_text_error: "Erreur IA (texte) : ",
    prompt_topic_short: "Écris un sujet court (ex : ouverture d'un café) :",
    alert_hashtag_need_topic: "Entre un sujet/texte court pour proposer des hashtags.",
    alert_ai_hashtag_error: "Erreur IA (hashtags) : ",

    label_weekly_days: "Jours de la semaine",
    day_mon: "Lun",
    day_tue: "Mar",
    day_wed: "Mer",
    day_thu: "Jeu",
    day_fri: "Ven",
    day_sat: "Sam",
    day_sun: "Dim",
    label_weekly_time: "Heure",
    label_weekly_start: "Début",
    label_weekly_end: "Fin (optionnel)",

    label_every_n_days: "Tous les combien de jours ?",
    label_every_time: "Heure",
    label_every_start: "Début",
    label_every_end: "Fin (optionnel)",

    btn_save_draft: "Enregistrer en brouillon",
    btn_submit_now: "Créer la publication",

    page_tasks_title: "Publications planifiées",
    page_drafts_title: "Brouillons",
    empty_list: "Aucun enregistrement pour le moment.",
    col_text: "Texte",
    col_platforms: "Plateformes",
    col_format: "Format",
    col_schedule: "Planification",
    col_type: "Type",
    type_one_shot: "Unique",
    type_weekly: "Hebdo",
    type_every: "Périodique",
    type_bulk: "Lot",
  },

  ja: {
    app_title: "MySocial パネル",
    nav_home: "ホーム",
    nav_create: "投稿作成",
    nav_scheduled: "予約",
    nav_drafts: "下書き",
    nav_queue: "キュー",
    nav_worker_logs: "ワーカーログ",
    nav_archive: "アーカイブ",
    nav_accounts: "アカウント",

    page_prepare_title: "投稿を準備",
    page_prepare_desc:
      "本文を作成し、プラットフォーム/形式を選び、メディアを追加してスケジュールします。単発・曜日指定・周期・一括に対応。",

    label_plan_type: "スケジュール種別",
    plan_one_shot: "単発（日時）",
    plan_weekly: "曜日指定（曜日 + 時刻）",
    plan_every_n_days: "N日ごと（周期）",
    plan_bulk: "一括（1行=1投稿）",

    label_post_text: "投稿本文",
    placeholder_post_text: "ここに入力...",

    label_bulk_lines: "一括内容（1行=1投稿）",
    placeholder_bulk_lines:
      "1行目: 1つ目の投稿\n2行目: 2つ目の投稿\n...",

    label_bulk_start: "一括開始日時",
    label_bulk_interval: "間隔（分）",
    helper_bulk_interval: "例: 60=毎時、1440=毎日",

    label_hashtags: "ハッシュタグ",
    placeholder_hashtags: "#目標 #幸せ #今日...",

    label_platforms: "プラットフォーム",
    label_format: "形式",
    format_normal: "通常",
    format_short: "Short/Reels",
    format_story: "ストーリー",

    label_media_type: "メディア種別",
    media_mixed: "混在",
    media_image: "画像のみ",
    media_video: "動画のみ",
    helper_media_type: "選択に応じてファイル選択がフィルタされます。",

    label_media_add: "メディア追加",
    label_one_shot_time: "単発スケジュール",

    label_weekly_days: "曜日",
    day_mon: "月",
    day_tue: "火",
    day_wed: "水",
    day_thu: "木",
    day_fri: "金",
    day_sat: "土",
    day_sun: "日",
    label_weekly_time: "時刻",
    label_weekly_start: "開始",
    label_weekly_end: "終了（任意）",

    label_every_n_days: "何日ごと？",
    label_every_time: "時刻",
    label_every_start: "開始",
    label_every_end: "終了（任意）",

    btn_save_draft: "下書き保存",
    btn_submit_now: "投稿を作成",

    page_tasks_title: "予約投稿",
    page_drafts_title: "下書き",
    empty_list: "まだありません。",
    col_text: "本文",
    col_platforms: "プラットフォーム",
    col_format: "形式",
    col_schedule: "日時",
    col_type: "種別",
    type_one_shot: "単発",
    type_weekly: "曜日指定",
    type_every: "周期",
    type_bulk: "一括",
  },
};

function t(key, lang) {
  const L = TRANSLATIONS[lang] || TRANSLATIONS.tr;
  return (L && L[key]) ?? (TRANSLATIONS.en[key] ?? (TRANSLATIONS.tr[key] ?? key));
}

function applyLanguage(lang) {
  const safeLang = TRANSLATIONS[lang] ? lang : "tr";

  document.documentElement.lang = safeLang;
  document.documentElement.dir = RTL_LANGS.has(safeLang) ? "rtl" : "ltr";
  document.body.classList.toggle("rtl", RTL_LANGS.has(safeLang));

  // Text nodes
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    el.textContent = t(key, safeLang);
  });

  // Placeholders
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    el.setAttribute("placeholder", t(key, safeLang));
  });

  document.dispatchEvent(new CustomEvent("lang:changed", { detail: { lang: safeLang } }));
}

document.addEventListener("DOMContentLoaded", () => {
  const stored = localStorage.getItem("lang") || "tr";
  applyLanguage(stored);

  const select = document.getElementById("lang-select");
  if (select) {
    select.value = stored;
    select.addEventListener("change", (e) => {
      const lang = e.target.value || "tr";
      localStorage.setItem("lang", lang);
      applyLanguage(lang);
    });
  }
});

// Eski kullanım varsa bozmayalım:
function changeLanguage(selectEl) {
  const lang = typeof selectEl === "string" ? selectEl : selectEl.value;
  localStorage.setItem("lang", lang);
  applyLanguage(lang);
}
