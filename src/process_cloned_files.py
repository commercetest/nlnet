import os
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
from loguru import logger

BATCH_SIZE = 5

def setup():
    load_dotenv()
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))



def process_files(supabase):
    while True:
        try:
            response = supabase.table('cloned_files')\
                        .select('id, file_path, file_name')\
                        .is_('processed_at','null')\
                        .limit(BATCH_SIZE)\
                        .execute()

            if not response.data:
                logger.info(f"No data for response_id : {response.id}")
                break

            for file in response.data:
                try:
                    has_test = 'test' in file['file_path'].lower()
                    supabase.table('cloned_files')\
                    .update({
                        'has_test_in_name_or_path' : has_test,
                        'processed_at' : datetime.utcnow().isoformat()
                    })\
                    .eq('id', file['id'])\
                    .execute()
                    logger.info(f"Processed file {file['id']}")

                except Exception as e:
                    logger.error(f"Error processing file {file['id']} : {e}")
                    continue

        except Exception as e:
            logger.error(f"Batch error: {e}")
            continue



def main():
    logger.add("logs/process_cloned_files.log", level="INFO", rotation="1 day")

    try:
        supabase = setup()
        process_files(supabase)
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    main()

