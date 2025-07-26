from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class Movie(models.Model):
    class Meta:
        verbose_name = _("فيلم")
        verbose_name_plural = _("أفلام")
        ordering = ['-rating']  # تغيير الترتيب حسب التقييم بدلاً من الرتبة
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['year']),
            models.Index(fields=['rating']),
            models.Index(fields=['genre']),
            models.Index(fields=['director']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['title', 'year'],
                name='unique_movie_title_year'
            )
        ]

    # إزالة حقل الرتبة (rank) لأنه غير مستخدم في الرفع
    title = models.CharField(
        verbose_name=_("عنوان الفيلم"),
        max_length=255,
        help_text=_("العنوان الكامل للفيلم"),
        null=False
    )
    
    genre = models.CharField(
        verbose_name=_("النوع"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("نوع الفيلم (أكشن، دراما، إلخ)")
    )
    
    director = models.CharField(
        verbose_name=_("المخرج"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("اسم المخرج أو المخرجين")
    )
    
    year = models.IntegerField(
        verbose_name=_("سنة الإنتاج"),
        validators=[
            MinValueValidator(1888),
            MaxValueValidator(2100)
        ],
        help_text=_("سنة إصدار الفيلم"),
        null=False
    )
    
    runtime = models.PositiveIntegerField(
        verbose_name=_("المدة (دقيقة)"),
        null=True,
        blank=True,
        validators=[MaxValueValidator(1000)],
        help_text=_("مدة الفيلم بالدقائق"),
        default=0  # إضافة قيمة افتراضية
    )
    
    rating = models.FloatField(
        verbose_name=_("التقييم"),
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(10.0)
        ],
        help_text=_("تقييم الفيلم من 10"),
        null=False,
        default=0.0  # إضافة قيمة افتراضية
    )
    
    votes = models.PositiveIntegerField(
        verbose_name=_("عدد التقييمات"),
        default=0,
        help_text=_("عدد التقييمات التي حصل عليها الفيلم")
    )
    
    # إزالة الحقول غير المستخدمة في عملية الرفع أو جعلها اختيارية
    actors = models.TextField(
        verbose_name=_("الممثلون"),
        blank=True,
        null=True,
        default="",
        help_text=_("أسماء الممثلين الرئيسيين")
    )
    
    revenue = models.FloatField(
        verbose_name=_("الإيرادات (مليون دولار)"),
        null=True,
        blank=True,
        default=0.0,
        validators=[MinValueValidator(0.0)],
        help_text=_("إيرادات الفيلم بالمليون دولار")
    )
    
    metascore = models.PositiveIntegerField(
        verbose_name=_("نتيجة ميتا"),
        null=True,
        blank=True,
        default=0,
        validators=[MaxValueValidator(100)],
        help_text=_("تقييم ميتاكرتيك من 100")
    )
    
    description = models.TextField(
        verbose_name=_("الوصف"),
        blank=True,
        null=True,
        default="",
        help_text=_("ملخص قصير للفيلم")
    )
    
    country = models.CharField(
        verbose_name=_("البلد"),
        max_length=100,
        blank=True,
        null=True,
        default="",
        help_text=_("بلد الإنتاج الرئيسي")
    )
    
    language = models.CharField(
        verbose_name=_("اللغة"),
        max_length=100,
        blank=True,
        null=True,
        default="",
        help_text=_("اللغة الأصلية للفيلم")
    )
    
    updated_at = models.DateTimeField(
        verbose_name=_("تاريخ التحديث"),
        auto_now=True,
        help_text=_("تاريخ آخر تحديث للبيانات")
    )

    def __str__(self):
        return f"{self.title} ({self.year}) - {self.rating}/10"

    def clean(self):
        """تنظيف وتحقق من البيانات قبل الحفظ"""
        super().clean()
        
        if self.title:
            self.title = self.title.strip()
        
        if self.director:
            self.director = self.director.strip()
        
        if self.genre and len(self.genre) > 255:
            self.genre = self.genre[:255]
        
        # تحقق من القيم المطلوبة
        if not self.title:
            raise ValidationError(_("عنوان الفيلم مطلوب"))
        if not self.year:
            raise ValidationError(_("سنة الإنتاج مطلوبة"))

    def save(self, *args, **kwargs):
        """تجاوز طريقة الحفظ للتأكد من التنظيف"""
        self.full_clean()  # تطبيق جميع عمليات التحقق
        super().save(*args, **kwargs)

    @property
    def rating_percentage(self):
        """حساب التقييم كنسبة مئوية"""
        return self.rating * 10 if self.rating else 0

    @property
    def is_popular(self):
        """تحقق إذا كان الفيلم شعبيًا"""
        return self.votes > 10000 or self.rating >= 8.0