from app.utils import Session, Slot
import time
import json
from datetime import datetime

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Please, enter login and password to print the slots, if necesssary add an interval as the third parameter.')
    parser.add_argument('--login', help='User login')
    parser.add_argument('--password', help='User password')
    parser.add_argument('--fulfilment_type', default='DELIVERY', help='Fulfilment type')
    parser.add_argument('--postcode', default='E14 3TJ', help='Post code')
    parser.add_argument('--interval', type=int, default=15, help='Interval to check available slots (in minutes)')

    args = parser.parse_args()

    cnt = 0

    while True:
        cnt += 1

        session = Session(args.login, args.password)

        slot = Slot(session=session, fulfilment_type=args.fulfilment_type, postcode=args.postcode)
        available_slots = slot.get_available_slots()

        print(f'------ Attempt number {cnt} --------------')

        if len(available_slots) == 0:
            time.sleep(args.interval*60)
        else:
            print(json.dumps(available_slots,indent=2))
            book=slot.book_slot(branch_id=753,
                                postcode='E14 3TJ',
                                address_id=40407464,
                                slot_type='DELIVERY',
                                start_date_time=datetime.strptime('2021-01-12 13:00:00', '%Y-%m-%d %H:%M:%S'),
                                end_date_time=datetime.strptime('2021-01-12 14:00:00', '%Y-%m-%d %H:%M:%S'))
            if not book:
                print('FAILURE!!!')
            break
