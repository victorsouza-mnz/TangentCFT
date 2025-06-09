#!/usr/bin/env python3
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.elasticsearch_service import ElasticsearchService
from collections import defaultdict


def formula_has_all_vectors(formula_source):
    """Check if a formula has all required vectors."""
    required_vectors = ["formula_vector", "slt_vector", "slt_type_vector", "opt_vector"]
    return all(
        formula_source.get(vec) is not None and len(formula_source.get(vec, [])) > 0
        for vec in required_vectors
    )


def get_posts_with_formulas(elastic_service, batch_size=100):
    """Get all posts that have formulas (formulas_count > 0)."""
    scroll_time = "5m"

    query = {
        "query": {"range": {"formulas_count": {"gt": 0}}},
        "size": batch_size,
        "_source": ["post_id", "formulas_count"],
    }

    result = elastic_service.es.search(
        index=elastic_service.posts_index_name, body=query, scroll=scroll_time
    )

    scroll_id = result["_scroll_id"]
    hits = result["hits"]["hits"]

    while hits:
        yield hits

        # Get next batch
        result = elastic_service.es.scroll(scroll_id=scroll_id, scroll=scroll_time)
        scroll_id = result["_scroll_id"]
        hits = result["hits"]["hits"]

    # Clean up scroll
    elastic_service.es.clear_scroll(scroll_id=scroll_id)


def get_formulas_for_post(elastic_service, post_id, expected_count):
    """Get all formulas for a specific post."""
    query = {
        "query": {"term": {"post_id": post_id}},
        "size": expected_count + 10,  # Add margin for safety
        "_source": [
            "formula_id",
            "post_id",
            "formula_vector",
            "slt_vector",
            "slt_type_vector",
            "opt_vector",
        ],
    }

    result = elastic_service.es.search(
        index=elastic_service.formulas_index_name, body=query
    )

    return result["hits"]["hits"]


def bulk_delete_posts(elastic_service, post_ids_to_delete):
    """Bulk delete posts."""
    if not post_ids_to_delete:
        return True

    bulk_data = []
    for post_id in post_ids_to_delete:
        action = {
            "delete": {"_index": elastic_service.posts_index_name, "_id": post_id}
        }
        bulk_data.append(action)

    try:
        response = elastic_service.es.bulk(operations=bulk_data, refresh=True)
        return not response.get("errors", False)
    except Exception as e:
        print(f"Error bulk deleting posts: {str(e)}")
        return False


def bulk_delete_formulas(elastic_service, formula_ids_to_delete):
    """Bulk delete formulas."""
    if not formula_ids_to_delete:
        return True

    bulk_data = []
    for formula_id in formula_ids_to_delete:
        action = {
            "delete": {"_index": elastic_service.formulas_index_name, "_id": formula_id}
        }
        bulk_data.append(action)

    try:
        response = elastic_service.es.bulk(operations=bulk_data, refresh=True)
        return not response.get("errors", False)
    except Exception as e:
        print(f"Error bulk deleting formulas: {str(e)}")
        return False


def run_cleanup(elastic_service, dry_run=False):
    """
    Main cleanup function that removes posts with incomplete formula data.

    Args:
        elastic_service: ElasticsearchService instance
        dry_run: If True, only show what would be deleted without actually deleting
    """
    print("🧹 Starting database cleanup...")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE DELETION'}")
    print("-" * 50)

    # Statistics
    stats = {
        "posts_processed": 0,
        "posts_to_delete": 0,
        "formulas_to_delete": 0,
        "posts_with_correct_data": 0,
    }

    # Collect items to delete
    posts_to_delete = []
    formulas_to_delete = []
    delete_batch_size = 100

    # Process posts in batches
    for post_batch in get_posts_with_formulas(elastic_service):
        for post_hit in post_batch:
            try:
                post_id = str(post_hit["_source"]["post_id"])
                expected_count = post_hit["_source"]["formulas_count"]

                stats["posts_processed"] += 1

                # Get formulas for this post
                formulas = get_formulas_for_post(
                    elastic_service, post_id, expected_count
                )

                # Check if post should be deleted
                should_delete = False
                reasons = []

                # Check formula count
                if len(formulas) != expected_count:
                    should_delete = True
                    reasons.append(
                        f"Expected {expected_count} formulas, found {len(formulas)}"
                    )

                # Check if all formulas have complete vectors
                incomplete_formulas = []
                for formula_hit in formulas:
                    if not formula_has_all_vectors(formula_hit["_source"]):
                        incomplete_formulas.append(formula_hit["_id"])

                if incomplete_formulas:
                    should_delete = True
                    reasons.append(
                        f"{len(incomplete_formulas)} formulas missing vectors"
                    )

                if should_delete:
                    stats["posts_to_delete"] += 1
                    stats["formulas_to_delete"] += len(formulas)

                    posts_to_delete.append(post_id)
                    formulas_to_delete.extend([f["_id"] for f in formulas])

                    print(f"❌ Post {post_id}: {', '.join(reasons)}")

                    # Process deletions in batches
                    if len(posts_to_delete) >= delete_batch_size:
                        if not dry_run:
                            # Delete posts
                            success_posts = bulk_delete_posts(
                                elastic_service, posts_to_delete
                            )
                            # Delete formulas
                            success_formulas = bulk_delete_formulas(
                                elastic_service, formulas_to_delete
                            )

                            if success_posts and success_formulas:
                                print(
                                    f"✅ Deleted batch: {len(posts_to_delete)} posts, {len(formulas_to_delete)} formulas"
                                )
                            else:
                                print(f"❌ Error deleting batch")
                        else:
                            print(
                                f"🔍 Would delete batch: {len(posts_to_delete)} posts, {len(formulas_to_delete)} formulas"
                            )

                        posts_to_delete = []
                        formulas_to_delete = []
                else:
                    stats["posts_with_correct_data"] += 1

                # Progress update
                if stats["posts_processed"] % 100 == 0:
                    print(
                        f"📊 Progress: {stats['posts_processed']} posts processed, {stats['posts_to_delete']} to delete"
                    )

            except Exception as e:
                print(
                    f"Error processing post {post_hit.get('_id', 'unknown')}: {str(e)}"
                )
                continue

    # Process final batch
    if posts_to_delete:
        if not dry_run:
            success_posts = bulk_delete_posts(elastic_service, posts_to_delete)
            success_formulas = bulk_delete_formulas(elastic_service, formulas_to_delete)

            if success_posts and success_formulas:
                print(
                    f"✅ Deleted final batch: {len(posts_to_delete)} posts, {len(formulas_to_delete)} formulas"
                )
            else:
                print(f"❌ Error deleting final batch")
        else:
            print(
                f"🔍 Would delete final batch: {len(posts_to_delete)} posts, {len(formulas_to_delete)} formulas"
            )

    # Print final statistics
    print("\n" + "=" * 50)
    print("📈 CLEANUP SUMMARY:")
    print(f"Posts processed: {stats['posts_processed']}")
    print(f"Posts with correct data: {stats['posts_with_correct_data']}")
    print(f"Posts {'to delete' if dry_run else 'deleted'}: {stats['posts_to_delete']}")
    print(
        f"Formulas {'to delete' if dry_run else 'deleted'}: {stats['formulas_to_delete']}"
    )

    if dry_run:
        print("\n⚠️  This was a DRY RUN - no data was actually deleted")
        print("Run with dry_run=False to perform actual deletion")
    else:
        print("\n✅ Cleanup completed successfully!")


def main():
    # Initialize Elasticsearch service
    elastic_service = ElasticsearchService()

    # Check if indices exist
    if not elastic_service.posts_index_exists():
        print("❌ Posts index does not exist!")
        return

    if not elastic_service.formulas_index_exists():
        print("❌ Formulas index does not exist!")
        return

    print("✅ Both indices found")

    # Ask user for confirmation
    print("\nThis script will delete posts and formulas with incomplete data.")

    # First run in dry-run mode to show what would be deleted
    print("\n🔍 Running DRY RUN first to show what would be deleted...")
    run_cleanup(elastic_service, dry_run=True)

    # Ask for confirmation to proceed
    response = (
        input("\nDo you want to proceed with the actual deletion? (yes/no): ")
        .lower()
        .strip()
    )

    if response == "yes":
        print("\n🚨 Proceeding with LIVE DELETION...")
        run_cleanup(elastic_service, dry_run=False)
    else:
        print("❌ Deletion cancelled by user")


if __name__ == "__main__":
    main()
