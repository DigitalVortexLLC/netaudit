from rest_framework.routers import DefaultRouter

from .views import CustomRuleViewSet, SimpleRuleViewSet

router = DefaultRouter()
router.register("rules/simple", SimpleRuleViewSet)
router.register("rules/custom", CustomRuleViewSet)

urlpatterns = router.urls
