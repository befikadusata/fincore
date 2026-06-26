from config.celery import app


@app.task(name='finance.check_overdue_installments')
def check_overdue_installments():
    from apps.finance.services.repayment_service import RepaymentService
    count = RepaymentService.check_overdue()
    return {'marked_overdue': count}
