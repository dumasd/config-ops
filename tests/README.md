# **Test Documentation**


```shell

liquibase update-sql --username=root --password=12345678 --url=jdbc:mysql://localhost:3306/test --changelog-file changelog-1.0.yaml --log-level=debug > liquibase_update_sql.log 

liquibase history --username=root --password=12345678 --url=jdbc:mysql://localhost:3306/liquibase --format TEXT

```
