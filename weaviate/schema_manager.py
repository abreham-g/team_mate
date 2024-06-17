import aiofiles
import json

class SchemaManager:
    def __init__(self, client, schema_file):
        self.client = client
        self.schema_file = schema_file

    async def is_valid(self):
        try:
            existing_schema = await self.client.get_schema()
            with open(self.schema_file, 'r') as f:
                new_schema = json.load(f)
            # Add validation logic here
            return existing_schema == new_schema
        except Exception as e:
            print(f"Error validating schema: {str(e)}")
            return False

    async def reset(self):
        try:
            await self.client.delete_all_classes()
            async with aiofiles.open(self.schema_file, 'r') as f:
                schema = await f.read()
                schema_dict = json.loads(schema)
                for class_info in schema_dict['classes']:
                    await self.client.create_class(class_info)
        except Exception as e:
            print(f"Error resetting schema: {str(e)}")
            raise
