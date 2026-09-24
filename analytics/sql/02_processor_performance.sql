with processor_monthly as (
    select
        date_trunc('month',t.simulation_date)::date as month,
        p.processor_name,
        count(pa.id) as attempt_volume,
        count(*) filter (where pa.attempt_status = 'CAPTURED') as captured_attempts,
        count(*) filter (where pa.attempt_status = 'FAILED') as failed_attempts,
        count(*) filter (where pa.attempt_status = 'CANCELED') as canceled_attempts,
        round(count(*) filter (where pa.attempt_status = 'CAPTURED')::numeric/ nullif(count(pa.id), 0) * 100,2) as success_rate,
        round(count(*) filter (where pa.attempt_status = 'FAILED')::numeric/ nullif(count(pa.id), 0) * 100,2) as failure_rate,
        round(sum(case when pa.attempt_status = 'CAPTURED'then t.amount * f.fx_rate else 0 end),2) as captured_gpv_usd,
        round(avg(extract(EPOCH from (pa.completed_at - pa.initiated_at))),2) as avg_processing_seconds,
        round((percentile_cont(0.95)within group (order by extract(epoch from (pa.completed_at - pa.initiated_at))))::numeric,2) as p95_processing_seconds from payment_attempts pa
    inner join transactions t
	on pa.transaction_fk = t.id
    inner join processors p
    on pa.processor_fk = p.id
    left join fx_rates f
    on t.simulation_date = f.rate_date
       and t.currency = f.source_currency
       and f.target_currency = 'USD'
    group by
        date_trunc('month',t.simulation_date)::date,p.processor_name)
select
    month,
    processor_name,
    attempt_volume,
    captured_attempts,
    failed_attempts,
    canceled_attempts,
    success_rate,
    failure_rate,
    captured_gpv_usd,
    avg_processing_seconds,
    p95_processing_seconds,
    round(
        attempt_volume::numeric/sum(attempt_volume) over (partition by month)* 100,2) as routing_share
from processor_monthly
order by
    month,
    processor_name;