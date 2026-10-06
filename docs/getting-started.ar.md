<div dir="rtl">

# دليل البداية

اللغة: [العربية](getting-started.ar.md) | [English](getting-started.md)

[الصفحة الرئيسية بالعربية](../README.ar.md) | [دليل الاستخدام العربي](usage-ar.md)

لـSbar Checkpoint مدخلان: استدعاء المهارة عبر المضيف الذي يشغّل وكيلك، أو تشغيل محركها المحلي مباشرةً. يتولى المضيف التنفيذ والمراجعة المستقلة وأي عمل يحتاج إلى متصفح أو صور. يسجل المحرك الأدلة ويتحقق من الانتقالات.

## التثبيت للمضيف

يمكن لـSkills CLI تثبيت نسخ على مستوى المستخدم للمضيفين الثلاثة:

<div dir="ltr">

```sh
npx skills add M7MMAD-OMAR/sbar-checkpoint --skill sbar-checkpoint -a codex claude-code hermes-agent -g
```

</div>

يتيح المثبت المرفق اختيار مضيف واحد، ويحترم مسارات المجلد الجذر المضبوطة:

<div dir="ltr">

```sh
git clone https://github.com/M7MMAD-OMAR/sbar-checkpoint.git
cd sbar-checkpoint
python3 skills/sbar-checkpoint/scripts/hosts.py paths --host all
python3 skills/sbar-checkpoint/scripts/install.py --host codex
```

</div>

اختر `--host claude` أو `--host hermes` بدلًا منه لهذين المضيفين. يرفض المثبت المجلدات والروابط الرمزية الموجودة. إن وجدت نسخة سابقة، افحصها واحفظ تعديلاتك المحلية قبل اختيار طريقة التحديث. لا يضبط المثبت النماذج أو بيانات الدخول أو الصلاحيات أو hooks العامة.

| المضيف | وجهة المستخدم الافتراضية | تخصيص الجذر | الاستدعاء |
| --- | --- | --- | --- |
| Codex | `~/.codex/skills/sbar-checkpoint` | `CODEX_HOME` | `$sbar-checkpoint` |
| Claude Code | `~/.claude/skills/sbar-checkpoint` | `CLAUDE_CONFIG_DIR` | `/sbar-checkpoint` |
| Hermes Agent | `~/.hermes/skills/sbar-checkpoint` | `HERMES_HOME` | `/sbar-checkpoint` |

يجب أن تكون مسارات تخصيص الجذر مطلقة. عند استخدام ملف شخصي مخصص في Hermes، اضبط `HERMES_HOME` على مجلده الفعلي المحسوم قبل استدعاء المثبت من طرفية خارجية.

يستخدم التثبيت داخل المشروع `.agents/skills` لـCodex و`.claude/skills` لـClaude Code و`.hermes/skills` لـHermes:

<div dir="ltr">

```sh
python3 skills/sbar-checkpoint/scripts/install.py \
  --host codex --scope project --project /absolute/path/to/project
```

</div>

يحتاج اكتشاف مشروع Hermes إلى جذر Git موثوق. قد تتغير سياسات اكتشاف المهارات لدى المضيف؛ راجع [مرجع المضيفين، بالإنجليزية](../skills/sbar-checkpoint/references/hosts.md) ومحول المضيف المناسب لإصدارك المثبت. تحتاج البيئات السحابية إلى إعداد توزيع وتنفيذ خاص بها.

بعد التثبيت، استخدم مسار المهارة الذي يوفره المضيف لتشغيل أداة التشخيص:

<div dir="ltr">

```text
python3 SKILL/scripts/doctor.py --host codex
```

</div>

استبدل `SKILL` بالمجلد الفعلي واختر المضيف الصحيح. تفحص أداة التشخيص متطلبات Python والمنصة والملفات التنفيذية والملفات القابلة للرصد. لا تتحقق من المصادقة أو اكتشاف المهارة أو توفر وكلاء مستقلين.

## اطلب نتيجة محددة

ابدأ في Codex بـ`$sbar-checkpoint`، وفي Claude Code وHermes التفاعلي بـ`/sbar-checkpoint`. يمكن لبقية الطلب وصف المهمة بلغة طبيعية. يدعم Hermes أيضًا التحميل الصريح غير التفاعلي:

<div dir="ltr">

```sh
hermes chat --oneshot --skills sbar-checkpoint --query-file prompt.txt
```

</div>

اذكر النتيجة والقيود والبيئة والتفويض في الطلب. الأمثلة التالية قوالب مهام بالعربية لتكييفها مع مستودعك، وليست ادعاءً بأن مشروعًا أو تكاملًا مع مضيف قد اختُبر.

### الإصلاح

```text
استخدم sbar-checkpoint لإصلاح تكرار تنفيذ الطلب في هذا المستودع.
حافظ على الواجهة العامة والتعديلات غير الملتزم بها. أعد إنتاج المشكلة أولًا،
ثم نفذ الإصلاح في بيئة اختبار محلية معزولة. اختبر إعادة المحاولة والتزامن
وحدود المؤسسات. أنت مفوض بتعديل المصدر والاختبارات اللازمة لهذا الإصلاح.
اطلب مراجعة مستقلة في سياق جديد. لا تنشر. سلّم السلوك المنفذ والأدلة الحالية
وأي حدود لم تسمح البيئة بالتحقق منها.
```

### التدقيق للقراءة فقط

```text
استخدم sbar-checkpoint بوضع audit لتدقيق صلاحيات الوصول في هذا المستودع.
لا تعدل المصدر أو الإعدادات أو البيانات. شغّل فقط فحوصًا تمت مراجعتها
للقراءة فقط، مع صلاحيات مقيدة حيث تتوفر. احفظ الخطة والنتائج خارج المصدر.
اربط كل ملاحظة بمتطلب ودليل من الملفات. اطلب مراجعة مستقلة للنتائج،
واذكر الأدلة الناقصة دون تسجيل نجاح لم يحدث.
```

قاعدة القراءة فقط جزء من عقد المضيف. المحرك ليس بيئة عزل؛ يمكن لملف تنفيذي مخطط أن يكتب ملفات ما لم تمنعه صلاحيات خارجية. استخدم وضع `plan` عندما تريد خطة فقط؛ يرفض هذا الوضع أوامر التنفيذ والاعتماد.

### ترحيل متعدد المراحل

```text
استخدم sbar-checkpoint لترحيل صيغة السجلات القديمة إلى صيغة ذات إصدار.
خطط مراحل مستقلة لقراءة الصيغتين، وتعبئة البيانات بشكل قابل للإعادة،
وتحويل الكتابة، وإزالة القراءة القديمة. حدد اعتماد كل مرحلة على سابقتها.
اختبر السجلات المرحّلة جزئيًا وإعادة التشغيل والانقطاع وحدود التراجع
في بيانات معزولة. ضمّن المخططات والإعدادات والاختبارات في نطاق المصدر.
استخدم مراجعين مستقلين للمواصفات والمعايير في المراحل الحساسة.
جهّز قرار التحويل للمراجعة وفق milestone. لا تشغل ترحيل إنتاج أو تنشر.
اذكر أي سلوك لمزود خارجي لا تثبته البيئة المحلية.
```

تدخل نطاقات المراحل السابقة ضمن بصمة المرحلة التابعة. قد يبطل تعديل قارئ التوافق بعد اعتماده إثبات تلك المرحلة وأدلة الترحيل اللاحقة معًا.

### تعديل واجهة بأدلة متطابقة

```text
استخدم sbar-checkpoint لإصلاح تخطيط نموذج الهاتف وفق المرجع المعتمد.
ضمّن المكونات والأنماط وبيانات الاختبار وفحوص التفاعل في النطاق.
قارن الحالة المحفوظة نفسها والدور واللغة نفسها في نافذة 390 في 844.
التقط الواجهة والمرجع وافحص الصورتين بأدوات صور فعلية، واختبر تركيز
لوحة المفاتيح ورسائل الخطأ والإرسال. اشترط مراجعة مصدر مستقلة وبوابة UI.
إذا تعذر فحص الصور أو التفاعل المطلوب، اترك البوابة دون إثبات. لا تنشر.
```

يجب أن يطابق تقرير الواجهة الهوية المخططة تمامًا، وأن يتضمن ملفي الالتقاط والمرجع. يفحص المحرك البيانات الوصفية وبصمات الملفات؛ يتولى المراجع الحكم البصري. راجع [صيغة تقرير الواجهة](../skills/sbar-checkpoint/references/cli.ar.md#ui-report).

### الإيقاف المؤقت والاستئناف

```text
أوقف تشغيل sbar-checkpoint الحالي مؤقتًا. أوقف الفحوص والأعمال الخلفية
التي تملكها هذه المهمة. احفظ المشروع والخطة والسجل والأدلة المكتملة.
صدّر الحالة والخطوة الآمنة التالية، ولا تبدأ عملًا جديدًا.
```

لاحقًا، فوّض الاستمرار صراحةً:

```text
استأنف تشغيل sbar-checkpoint الموجود. اقرأ الحالة الحالية، وتحقق من
الأوامر المعلقة وأي أثر خارجي ملتبس، ثم تابع المراحل الجاهزة وفق النطاق
وسياسة الموافقة الأصلية. جدد الفحوص والمراجعات التي أصبحت قديمة.
```

لا يتجاوز الانتقال إلى مضيف آخر أو رسالة متابعة أخرى طلب إيقاف مؤقت صريحًا. احتفظ بمساري المشروع والتشغيل نفسيهما، واستخدم منسقًا واحدًا في كل مرة.

<a id="local-engine-walkthrough"></a>

## تجربة المحرك المحلي خطوة بخطوة

يوضح هذا الإصلاح الصغير آلية الأوامر. تغيير بهذا الحجم يحتاج عادةً إلى تحقق مباشر. نفذه من المستودع المنسوخ في طرفية POSIX مع Python 3.10 أو أحدث. يستخدم مساحة عمل مؤقتة ولا ينشئ خدمات إنتاج. توضح هذه الأوامر بيانات اختبار محلية، وليست اختبار قبول لمضيف.

ابدأ بتحديد المحرك المرفق وإنشاء مواقع متجاورة للمشروع والخطة والتشغيل:

<div dir="ltr">

```sh
SKILL="$PWD/skills/sbar-checkpoint"
ENGINE="$SKILL/scripts/workflow.py"
WORK="$(mktemp -d)"
PROJECT="$WORK/project"
RUN="$WORK/run"
mkdir -p "$PROJECT/tests"
python3 "$SKILL/scripts/doctor.py" --host codex
```

</div>

يجب أن يقع التشغيل خارج شجرة المشروع. أبق الخطط ومدخلات المراجع وتقاريره خارج نطاقات المصدر أيضًا. لا تضع أسرارًا في الأوامر أو الخطط أو السجلات.

أنشئ التنفيذ المعيب واختباري قبول:

<div dir="ltr">

```sh
cat > "$PROJECT/total.py" <<'PY'
def total_cents(subtotal, fee):
    return subtotal - fee
PY
cat > "$PROJECT/tests/test_total.py" <<'PY'
import unittest
from total import total_cents

class TotalTests(unittest.TestCase):
    def test_adds_fee(self):
        self.assertEqual(total_cents(1200, 75), 1275)

    def test_zero_fee(self):
        self.assertEqual(total_cents(1200, 0), 1200)
PY
```

</div>

أنشئ خطة قبل التنفيذ. يستخدم الأمر مصفوفة `argv` بدل سلسلة نصية للطرفية. يتطلب محلل `unittest` اختبارات منفذة فعليًا؛ فحص يعتمد على رمز الخروج وحده لا يحقق شرط عدد الاختبارات.

<div dir="ltr">

```sh
cat > "$WORK/plan.json" <<'JSON'
{
  "schema_version": 1,
  "mode": "repair",
  "approval": "delegated",
  "environment": "local-isolated",
  "requirements": [
    {"id": "R1", "text": "Add the fee to the subtotal in integer cents"},
    {"id": "R2", "text": "Preserve the subtotal when the fee is zero"}
  ],
  "checkpoints": [{
    "id": "core",
    "title": "Repair fee calculation",
    "covers": ["R1", "R2"],
    "depends_on": [],
    "scope": ["total.py", "tests/test_total.py"],
    "gates": {
      "behavior": {
        "kind": "command",
        "checks": [{
          "id": "unit",
          "argv": ["python3", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
          "parser": "unittest", "min_tests": 2,
          "timeout_seconds": 60, "max_attempts": 3
        }]
      },
      "review": {"kind": "review", "reviewers": 1, "axes": ["specification"]},
      "ui": {"kind": "not_applicable", "reason": "No visible interface change"}
    }
  }]
}
JSON
python3 "$ENGINE" init --run "$RUN" --project "$PROJECT" --plan "$WORK/plan.json"
python3 "$ENGINE" start --run "$RUN" --checkpoint core --actor implementer
python3 "$ENGINE" check --run "$RUN" --checkpoint core --check unit --token baseline
```

</div>

يجب أن يعيد الفحص الأولي رمز خروج 1 ويسجل اختبارًا فاشلًا. اقرأ مخرجاته، ثم أصلح التنفيذ وشغّل استدعاءً جديدًا:

<div dir="ltr">

```sh
cat > "$PROJECT/total.py" <<'PY'
def total_cents(subtotal, fee):
    return subtotal + fee
PY
python3 "$ENGINE" check --run "$RUN" --checkpoint core --check unit --token repaired
python3 "$ENGINE" status --run "$RUN"
```

</div>

تُشغّل الفحوص من مجلد المشروع. يرتبط الرمز المكتمل بالمصدر والخطة والفحص. يؤدي تكرار `repaired` على المصدر نفسه إلى إعادة النتيجة المحفوظة دون تنفيذ جديد. يرفض المحرك ذلك الرمز عند تغير المصدر؛ استخدم رمزًا جديدًا للمصدر الجديد. لا تعالج هذه الآلية الآثار الجانبية للمدفوعات أو الترحيلات.

جهّز مدخلًا لمراجع مستقل في سياق جديد خارج المشروع والتشغيل:

<div dir="ltr">

```sh
python3 "$SKILL/scripts/hosts.py" review-packet \
  --run "$RUN" --checkpoint core --reviewer independent-reviewer \
  --axis specification --output "$WORK/review-input.json"
```

</div>

أعطِ وكيلًا فرعيًا في سياق جديد أو عملية مضيف جديدة مفوضة تلك الحزمة وقواعد المشروع والمصدر داخل النطاق و[عقد تقرير المراجعة، بالإنجليزية](../skills/sbar-checkpoint/references/roles.md). اطلب منه فحص التنفيذ والاختبارات وحفظ تقريره الفعلي في `$WORK/review.json`. يجب أن يتحقق من البصمات الحالية باستخدام `hosts.py review-state` قبل الرد، وأن يتجنب الأحكام السابقة. لا يجعل اسم منفذ جديد وحده المراجع مستقلًا.

يحتوي التقرير على `source_hash` و`plan_hash` الحاليين واسم المراجع ومحور المراجعة وحكمه الفعلي وملاحظاته. لا تنشئ بنفسك تقرير نجاح لإكمال المثال. إذا تعذرت المراجعة المستقلة، تظل المرحلة دون إثبات.

بعد وجود تقرير نجاح فعلي ومعالجة أي ملاحظات بأدلة جديدة:

<div dir="ltr">

```sh
python3 "$ENGINE" review --run "$RUN" --checkpoint core --report "$WORK/review.json"
python3 "$ENGINE" prove --run "$RUN" --checkpoint core
python3 "$ENGINE" accept --run "$RUN" --checkpoint core
python3 "$ENGINE" export --run "$RUN"
python3 "$SKILL/scripts/viewer.py" --run "$RUN" --output "$WORK/report.html"
```

</div>

يستخدم الاعتماد وفق `delegated` التفويض القائم. في سياسة `milestone` أو `checkpoint`، يحتاج `accept` أيضًا إلى `--approval-note` لتسجيل التفويض الفعلي ومصدره. لا يصادق الأمر على تلك الملاحظة ولا ينشر شيئًا.

يكتب التصدير `status.json` و`resume.md` في مجلد التشغيل. ينشئ العارض تقرير HTML محليًا. يؤدي تعديل المصدر بعد الاعتماد إلى تقادم الأدلة السابقة؛ افحص الحالة الحالية وأعد تشغيل البوابات المتأثرة.

لتشغيل قائم، استخدم الأوامر التالية للإيقاف المؤقت والاستئناف:

<div dir="ltr">

```sh
python3 "$ENGINE" pause --run "$RUN" --reason 'User requested a pause'
python3 "$ENGINE" export --run "$RUN"
# Run only after the user explicitly resumes the work:
python3 "$ENGINE" resume --run "$RUN"
python3 "$ENGINE" status --run "$RUN"
```

</div>

يحفظ الإيقاف المؤقت والإلغاء الملفات، وينهيان مجموعات عمليات الفحص المملوكة للتشغيل. بعد تعطل العملية، افحص الأوامر المعلقة والآثار الخارجية قبل الاستئناف. لا تكرر عملية خارجية ذات نتيجة ملتبسة دون تحقق. يغطي [مرجع الأوامر](../skills/sbar-checkpoint/references/cli.ar.md) الرموز المعلقة واستعادة السجل والمراجعات المتوقعة وتغييرات الخطة وعقود محللات المخرجات والصيغ الدقيقة.

</div>
