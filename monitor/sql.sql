SELECT c.name, p.name, j.jobbytes, j.realendtime, j.starttime, j.jobfiles 
                     FROM client c 
                     LEFT JOIN LATERAL ( 
                       SELECT DISTINCT ON (j.poolid) j.jobbytes, j.realendtime, j.poolid,  j.starttime, j.jobfiles 
                       FROM job j 
                       WHERE j.clientid = c.clientid  AND j.jobstatus IN ('T', 'W') AND j.level IN ('F', 'I', 'D') AND j.type IN ('B', 'C') 
                       ORDER BY j.poolid, j.realendtime DESC 
                     ) j ON TRUE 
                     LEFT JOIN pool p ON p.poolid = j.poolid;
