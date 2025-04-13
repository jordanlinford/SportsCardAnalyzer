import pytest
import asyncio
from datetime import datetime
from modules.core.models import Card, Collection, UserProfile
from modules.core.repositories import CardRepository, CollectionRepository, UserRepository
from modules.core.repository import RepositoryError, DocumentNotFoundError

@pytest.fixture
def card_repository():
    return CardRepository()

@pytest.fixture
def collection_repository():
    return CollectionRepository()

@pytest.fixture
def user_repository():
    return UserRepository()

@pytest.mark.asyncio
async def test_card_repository_basic_operations(card_repository):
    # Test create
    card = Card(
        player_name="Test Player",
        year=2023,
        card_set="Test Set",
        card_number="1",
        condition="Mint",
        purchase_price=100.0,
        purchase_date=datetime.now(),
        current_value=150.0,
        last_updated=datetime.now(),
        notes="Test card",
        photo="test.jpg",
        roi=50.0,
        tags=["test", "baseball"]
    )
    
    created_card = await card_repository.create(card)
    assert created_card.id is not None
    assert created_card.player_name == "Test Player"
    
    # Test get
    retrieved_card = await card_repository.get(created_card.id)
    assert retrieved_card is not None
    assert retrieved_card.player_name == "Test Player"
    
    # Test update
    retrieved_card.notes = "Updated notes"
    updated_card = await card_repository.update(retrieved_card)
    assert updated_card.notes == "Updated notes"
    
    # Test delete
    result = await card_repository.delete(created_card.id)
    assert result is True
    
    # Verify deletion
    deleted_card = await card_repository.get(created_card.id)
    assert deleted_card is None

@pytest.mark.asyncio
async def test_collection_repository_basic_operations(collection_repository):
    # Test create
    collection = Collection(
        name="Test Collection",
        description="Test description",
        cards=[],
        tags=["test"],
        is_public=True
    )
    
    created_collection = await collection_repository.create(collection)
    assert created_collection.id is not None
    assert created_collection.name == "Test Collection"
    
    # Test get
    retrieved_collection = await collection_repository.get(created_collection.id)
    assert retrieved_collection is not None
    assert retrieved_collection.name == "Test Collection"
    
    # Test update
    retrieved_collection.description = "Updated description"
    updated_collection = await collection_repository.update(retrieved_collection)
    assert updated_collection.description == "Updated description"
    
    # Test delete
    result = await collection_repository.delete(created_collection.id)
    assert result is True
    
    # Verify deletion
    deleted_collection = await collection_repository.get(created_collection.id)
    assert deleted_collection is None

@pytest.mark.asyncio
async def test_user_repository_basic_operations(user_repository):
    # Test create
    user = UserProfile(
        display_name="Test User",
        email="test@example.com",
        preferences={"theme": "dark"},
        collections=[]
    )
    
    created_user = await user_repository.create(user)
    assert created_user.id is not None
    assert created_user.display_name == "Test User"
    
    # Test get
    retrieved_user = await user_repository.get(created_user.id)
    assert retrieved_user is not None
    assert retrieved_user.display_name == "Test User"
    
    # Test update
    retrieved_user.preferences["theme"] = "light"
    updated_user = await user_repository.update(retrieved_user)
    assert updated_user.preferences["theme"] == "light"
    
    # Test delete
    result = await user_repository.delete(created_user.id)
    assert result is True
    
    # Verify deletion
    deleted_user = await user_repository.get(created_user.id)
    assert deleted_user is None

@pytest.mark.asyncio
async def test_card_repository_search_and_filter(card_repository):
    # Create test cards
    cards = [
        Card(
            player_name="Player A",
            year=2023,
            card_set="Set A",
            card_number="1",
            condition="Mint",
            tags=["baseball"]
        ),
        Card(
            player_name="Player B",
            year=2022,
            card_set="Set B",
            card_number="2",
            condition="Near Mint",
            tags=["baseball"]
        )
    ]
    
    created_cards = await card_repository.batch_create(cards)
    
    # Test search
    search_results = await card_repository.search("Player A")
    assert len(search_results) > 0
    assert any(card.player_name == "Player A" for card in search_results)
    
    # Test get_by_year
    year_results = await card_repository.get_by_year(2023)
    assert len(year_results) > 0
    assert all(card.year == 2023 for card in year_results)
    
    # Test get_by_tag
    tag_results = await card_repository.get_by_tag("baseball")
    assert len(tag_results) > 0
    assert all("baseball" in card.tags for card in tag_results)
    
    # Cleanup
    for card in created_cards:
        await card_repository.delete(card.id)

@pytest.mark.asyncio
async def test_collection_repository_card_management(collection_repository, card_repository):
    # Create test collection
    collection = Collection(
        name="Test Collection",
        description="Test description",
        cards=[],
        tags=["test"],
        is_public=True
    )
    created_collection = await collection_repository.create(collection)
    
    # Create test card
    card = Card(
        player_name="Test Player",
        year=2023,
        card_set="Test Set",
        card_number="1"
    )
    created_card = await card_repository.create(card)
    
    # Test add_card
    updated_collection = await collection_repository.add_card(created_collection.id, created_card.id)
    assert created_card.id in updated_collection.cards
    
    # Test get_cards
    cards = await collection_repository.get_cards(created_collection.id)
    assert len(cards) == 1
    assert cards[0].id == created_card.id
    
    # Test remove_card
    updated_collection = await collection_repository.remove_card(created_collection.id, created_card.id)
    assert created_card.id not in updated_collection.cards
    
    # Cleanup
    await collection_repository.delete(created_collection.id)
    await card_repository.delete(created_card.id)

@pytest.mark.asyncio
async def test_user_repository_collection_management(user_repository, collection_repository):
    # Create test user
    user = UserProfile(
        display_name="Test User",
        email="test@example.com",
        preferences={},
        collections=[]
    )
    created_user = await user_repository.create(user)
    
    # Create test collection
    collection = Collection(
        name="Test Collection",
        description="Test description",
        cards=[],
        tags=["test"],
        is_public=True
    )
    created_collection = await collection_repository.create(collection)
    
    # Test add_collection
    updated_user = await user_repository.add_collection(created_user.id, created_collection.id)
    assert created_collection.id in updated_user.collections
    
    # Test get_collections
    collections = await user_repository.get_collections(created_user.id)
    assert len(collections) == 1
    assert collections[0].id == created_collection.id
    
    # Test remove_collection
    updated_user = await user_repository.remove_collection(created_user.id, created_collection.id)
    assert created_collection.id not in updated_user.collections
    
    # Cleanup
    await user_repository.delete(created_user.id)
    await collection_repository.delete(created_collection.id) 