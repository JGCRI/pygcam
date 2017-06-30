drop view if exists ci;
drop view if exists param;
drop view if exists result;
drop view if exists status;

create view status as
  select s."simId", e."expName", status, count(*) from run r, experiment e, sim s
  where s."simId" = r."simId" and e."expId" = r."expId"
  group by s."simId", e."expName", status order by s."simId", e."expName", status;

create view result as
  select o."runId", r."simId", r."expId", r."trialNum", e."expName", op.name, o.value
  from outvalue o, output op, run r, experiment e
  where e."expId" = r."expId" and o."runId" = r."runId" and o."outputId" = op."outputId";

create view param AS
  select iv."simId", iv."trialNum", ip."paramName", iv.value
  from input ip, invalue iv
  where ip."inputId" = iv."inputId";

create view ci AS
  select * from result where name like 'ci%';

drop view if exists runinfo;

create view runinfo AS
  select r.runid, r.simid, r.trialnum, e.expname, r.status
  from run r, experiment e
  where r.expid=e.expid;
