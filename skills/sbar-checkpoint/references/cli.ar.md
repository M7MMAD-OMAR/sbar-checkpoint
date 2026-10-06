<div dir="rtl">

# مرجع أوامر المحرك

[English](cli.md) | العربية

يحتاج المحرك Python 3.10 أو أحدث وبيئة POSIX تدعم مجموعات العمليات وأقفال الملفات الاستشارية. يستخدم المكتبة القياسية فقط. تُنفذ الأوامر من مجلد المشروع باستخدام مصفوفة `argv` المخططة نفسها، ولا يضيف المحرك shell تلقائيًا. الخطة مدخل تنفيذي موثوق: يمكن للأمر أن يستدعي shell أو أداة شبكة صراحة. المحرك ليس sandbox لنظام التشغيل.

## الأوامر

<div dir="ltr">

```sh
python3 scripts/workflow.py init --run /absolute/run --project /absolute/project --plan plan.json
python3 scripts/workflow.py status --run /absolute/run
python3 scripts/workflow.py start --run /absolute/run --checkpoint cp1 --actor implementer
python3 scripts/workflow.py check --run /absolute/run --checkpoint cp1 --check tests --token stable-invocation-key
python3 scripts/workflow.py review --run /absolute/run --checkpoint cp1 --report review.json
python3 scripts/workflow.py ui --run /absolute/run --checkpoint cp1 --report ui.json
python3 scripts/workflow.py prove --run /absolute/run --checkpoint cp1
python3 scripts/workflow.py accept --run /absolute/run --checkpoint cp1
python3 scripts/workflow.py pause --run /absolute/run --reason 'Owner pause'
python3 scripts/workflow.py resume --run /absolute/run
python3 scripts/workflow.py cancel --run /absolute/run --reason 'Owner cancellation'
python3 scripts/workflow.py revise --run /absolute/run --plan revised-plan.json
python3 scripts/workflow.py export --run /absolute/run
python3 scripts/workflow.py recover --run /absolute/run --truncate-final-line
```

</div>

تقبل جميع أوامر التعديل باستثناء `init` الخيار `--expected-revision N`. اختلاف رقم المراجعة يمنع التعديل. يعيد `status` الرقم الحالي. تطبع الأوامر الناجحة كائن JSON على stdout. تطبع أخطاء التحقق `{"error":"reason"}` على stderr وتنتهي بالرمز 2. يطبع الفحص الفاشل أو غير الصالح دليله المسجل على stdout وينتهي بالرمز 1. لا يغير `status` و`export` رقم مراجعة السجل. تعيد مراجعة الخطة ضبط حالات المراحل مع حفظ اللقطات السابقة في سجل الأحداث. يجب أن يكون مجلد التشغيل خارج شجرة المشروع.

يحتاج `accept` مرحلة مُثبتة بالأدلة الحالية. عند استخدام موافقات `milestone` أو `checkpoint` أضف `--approval-note 'User authorization and its source'` لتسجيل التفويض الفعلي ومصدره. هذه ملاحظة يصرح بها المشغّل وليست مصادقة على هوية المستخدم. لا يحتاج وضع `delegated` هذه الملاحظة. لا تنشر هذه الواجهة ولا تدمج ولا توسع صلاحياتك.

## صيغة الخطة

<div dir="ltr">

```json
{
  "schema_version": 1,
  "mode": "feature",
  "approval": "delegated",
  "environment": "local-isolated",
  "requirements": [{"id": "R1", "text": "Round the total correctly"}],
  "checkpoints": [{
    "id": "cp1",
    "title": "Correct calculation",
    "covers": ["R1"],
    "depends_on": [],
    "scope": ["src.py", "test_src.py"],
    "gates": {
      "behavior": {
        "kind": "command",
        "checks": [{"id": "tests", "argv": ["python3", "-m", "unittest", "-v"],
                    "parser": "unittest", "min_tests": 1,
                    "timeout_seconds": 60, "max_attempts": 3}]
      },
      "review": {"kind": "review", "reviewers": 1, "axes": ["specification"]},
      "ui": {"kind": "not_applicable", "reason": "No visible interface change"}
    }
  }]
}
```

</div>

الأوضاع: `feature` و`migration` و`repair` و`audit` و`plan`. يرفض وضع `plan` البدء والفحص والإثبات والاعتماد. وضع التدقيق وبيئة القراءة فقط عقد يلتزم به الوكيل؛ يكتشف المحرك تغير المصدر أثناء الفحص لكنه لا يمنع أمرًا تنفيذيًا من الكتابة. اختر أوامر قراءة فقط تمت مراجعتها، واستخدم صلاحيات خارجية مقيدة عند الحاجة.

سياسات الموافقة: `delegated` و`milestone` و`checkpoint`. البيئات: `local-isolated` و`read-only` و`staging` و`production`. يحتاج الإنتاج الحقل `production_authorization: {"allowed": true, "reason": "specific existing authorization"}`. يوثق هذا الحقل تفويضًا قائمًا ولا يتحقق من هويته. تدخل البيئة في بصمة الخطة وبيانات الأدلة، لكنها ليست حدًا تلقائيًا للشبكة أو الأسرار.

يجب أن تغطي مرحلة واحدة على الأقل كل متطلب، أو تستبعده صراحة باستخدام `exclusions: [{"id":"R2","reason":"Explicitly outside this delivery"}]`. يجب أن تشير الاعتمادات إلى مراحل معروفة دون دورات. قيم النطاق مسارات ملفات نسبية آمنة أو أنماط ملفات. يمكن ذكر ملفات جديدة قبل إنشائها. يُرفض النمط الذي يطابق مجلدًا؛ استخدم `src/**/*.py` بدل `src/**`. تُرفض المسارات المطلقة واجتياز المجلد الأب والروابط الرمزية التي تخرج من الشجرة. تُستبعد مجلدات الاعتمادات المولدة الشائعة. ضمّن اختبارات القبول والعقود والإعدادات والملفات المؤثرة. تدخل نطاقات المراحل السابقة في بصمات المراحل التابعة عبر سلسلة الاعتماد. لا يستطيع المحرك استنتاج اعتماد أغفلته أو حماية الأدلة من تأثير ملف لم تذكره.

تغطي بصمة المصدر هوية مسار المشروع والجهاز وinode وجذر Git، وأنماط النطاق وأسماء الملفات المطابقة وبياناتها وصلاحياتها. تشمل التعديلات غير الملتزم بها والملفات غير المتتبعة عندما يطابقها النطاق. لا تعني أن كل ملفات الجهاز مشمولة.

## بوابة السلوك

المحللات المدعومة:

- `unittest`: يحتاج ملخصًا واحدًا بصيغة `Ran N tests in ...` ونتيجة نهائية `OK` أو `FAILED`. يسجل أعداد الفشل والأخطاء والتجاوز، ويشترط تنفيذ `min_tests` على الأقل دون الاختبارات المتجاوزة.
- `json`: يطبع الأمر كائن JSON واحدًا فقط، فيه الحقول الصحيحة غير السالبة `total` و`failed` و`skipped`. لا يتجاوز مجموع الفشل والتجاوز العدد الكلي. يجب أن يبلغ العدد غير المتجاوز حد `min_tests`.
- `exit`: للفحص الشكلي والبناء والأدوات التي لا تعطي عدد اختبارات. يحتاج `min_tests: 0` ولا يسجل اختبارات فعلية. لا تستخدمه للادعاء بأن اختبارات قبول نُفذت.

لكل أمر مهلة وعدد محاولات محددان. الحد الأقصى للمخرجات 4 MiB. انتهاء المهلة أو المقاطعة أو تغير المصدر أثناء التشغيل أو تجاوز حد المخرجات أو فشل التنفيذ يجعل الدليل غير صالح. تُنهى مجموعة العمليات عند انتهاء الأمر. يمكن لعملية تابعة أن تتجاوز هذا الحد إذا أنشأت جلسة مستقلة عمدًا؛ استخدم مشرفًا خارجيًا عند الحاجة لعزل أقوى. لا تخطط أوامر هدفها ترك خوادم تعمل.

يربط رقم الاستدعاء `--token` مصدرًا وخطة وفحصًا محددين بصورة دائمة. تكرار رقم مكتمل يعيد الدليل الأصلي دون تشغيل الأمر مجددًا. تغير المصدر أو الخطة يرفض الرقم. يمكن إعادة الفحص الفاشل برقم جديد حتى حد `max_attempts` للمصدر والفحص والخطة نفسها. لا يُعاد رقم مقاطَع. غياب الرقم يولد UUID جديدًا، وهذا مناسب فقط للفحوص التي تنوي تنفيذها مجددًا.

## تقرير المراجعة

خذ `source_hash` و`plan_hash` من الحالة الحالية قبل تسليم المهمة للوكيل المستقل مباشرة. استورد تقريرًا بهذه البنية:

<div dir="ltr">

```json
{
  "source_hash": "current source hash",
  "plan_hash": "current plan hash",
  "reviewer": "independent-agent-1",
  "axis": "specification",
  "verdict": "pass",
  "findings": [],
  "artifacts": []
}
```

</div>

الحكم `verdict` هو `pass` أو `fail` أو `invalid`. يجب أن يختلف المراجع عن المنفذ. اسم المراجع تصريح بالهوية وليس هوية مشفرة. بوابة مراجعين تحتاج اسمين مختلفين ومحوري المراجعة المخططين. المحوران الافتراضيان `specification` و`standards`؛ بوابة مراجع واحد تستخدم `specification` افتراضيًا.

كل ملاحظة تحتاج `id` و`severity` بقيمة `blocker` أو `major` أو `minor`، و`evidence` غير فارغ. يمكن إضافة `resolution` بقيمة `fixed` أو `dismissed` أو `deferred`، وأي حل يحتاج `reason` غير فارغ. لا يقبل تقرير ناجح ملاحظات غير محلولة. يمكن تأجيل الملاحظات البسيطة فقط عندما تتضمن الخطة سياسة `minor_deferral_policy` غير فارغة، مع تعليم الملاحظة بأنها مؤجلة وتفسير السبب. لا يسمح تأجيل ملاحظة مانعة أو كبيرة بتسجيل النجاح. يجب أن يتحقق المراجع من دليل الإصلاح أو رفض الملاحظة، ولا يعتمد على تصريح المنفذ وحده.

مسارات الملفات المرفقة اختيارية، وتُفسر نسبة إلى مجلد التقرير. لا يجوز أن تجتاز المجلد الأب، ويجب أن تبقى داخل مجلد التقرير بعد حل الروابط الرمزية. ينسخ المحرك الملفات إلى مجلد أدلته ويحسب بصماتها. يرفض تقارير البصمات القديمة قبل الاستيراد.

<a id="ui-report"></a>

## تقرير الواجهة

بوابة الواجهة المطلوبة تحمل `kind: "ui"` وحقل `identity` الذي يتضمن `fixture` و`language` و`reference` و`role` و`state` و`viewport: [width,height]`. أضف هوية المقياس وحالة الشبكة وبصمة بيانات الاختبار عندما تتطلب المقارنة ذلك. يجب أن تطابق هوية التقرير الكائن المخطط كاملًا وبالضبط.

<div dir="ltr">

```json
{
  "source_hash": "current source hash",
  "plan_hash": "current plan hash",
  "reviewer": "visual-reviewer",
  "verdict": "pass",
  "identity": {
    "fixture": "invoice-1",
    "language": "ar",
    "reference": "approved prototype v1",
    "role": "manager",
    "state": "saved",
    "viewport": [390, 844]
  },
  "artifacts": {"capture": "capture.png", "reference": "reference.png"}
}
```

</div>

ملفا الالتقاط والمرجع مطلوبان. اختلاف البيانات الوصفية يسجل `invalid` ويمنع الإثبات. تكشف البصمات تعديل الملفات لاحقًا. يتحقق المحرك من وجود الملفات وبياناتها ولا يفك الصور أو يحكم على المظهر. يجب أن يفحص المراجع الصور فعليًا وينفذ اختبارات التفاعل المطلوبة؛ نجاح استيراد التقرير وحده لا يثبت جودة الواجهة.

## السجل والتوقف والاستئناف

`events.jsonl` هو سجل الأحداث المعتمد والمترابط بالبصمات. `state.json` إسقاط مساعد ولا يُعتمد مصدرًا للحقيقة. يحسب `status` صلاحية الأدلة من بصمات المصدر الحالية والملفات المنسوخة. تظهر المراحل المعتمدة أو المثبتة ذات الأدلة القديمة بحالة `verifying`، ولا تتقدم المراحل التابعة حتى تُعتمد المراحل السابقة بالأدلة الحالية.

يحفظ التوقف والإلغاء الملفات. يفحص الأمر الجاري حالة التشغيل كل 100 مللي ثانية وينهي مجموعة عملياته عند التوقف أو الإلغاء. مقاطعة لوحة المفاتيح توقف التشغيل مؤقتًا. انهيار المحرك يترك أمرًا معلقًا: أوقف التشغيل صراحة، وافحص المشروع والخدمات، ثم استأنف لتعليم أرقام الاستدعاء المتروكة بأنها مقاطعة. يُرفض الاستئناف إذا كانت عملية المحرك لأمر معلق ما تزال حية، لمنع سباق التوقف والاستئناف. لا تفترض أن انهيار الجهاز يثبت توقف كل الآثار الخارجية.

سطر أخير غير مكتمل في السجل يمنع جميع الأوامر العادية. يحفظ `recover --truncate-final-line` نسخة من البيانات غير المكتملة، ويحتفظ بالسجلات الكاملة، ويوقف التشغيل للفحص. لا يصلح سجلًا كاملًا فاسدًا ولا يقبل تعديل الحالة يدويًا. البصمات تكشف التلف وليست حماية موثقة ضد التلاعب. من يستطيع تعديل المحرك أو إعادة حساب سلسلة السجل يمكنه اختلاق تاريخ. استخدم متحققًا خارجيًا وصلاحيات مقيدة عندما تحتاج حد ثقة أقوى.

يكتب `export` ملفي `status.json` و`resume.md` لوصف البوابات الحالية والخطوة الآمنة التالية. لا يعيد تشغيل خدمة أو تنفيذ أمر.

</div>
