from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .asset_engine import project_docs


@api_view(["POST"])
def generate_project_assets(request):
    """
    API endpoint to trigger project document generation.
    """
    try:
        project_docs()
        return Response(
            {"message": "✅ Project documents generated successfully."},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

