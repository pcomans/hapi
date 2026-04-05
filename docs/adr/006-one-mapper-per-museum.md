# ADR-006: One Mapper per Museum, No Universal Parser

## Status
Accepted

## Context
Museum data formats differ significantly. A universal parser would need to handle every museum's field naming, structure, and conventions.

## Decision
Each museum gets its own mapper implementing `MapperProtocol`. Adding a museum means writing a new mapper, not modifying a shared one.

## Consequences
- More total code than a universal parser, but dramatically safer — changing the Brooklyn mapper cannot break Met normalization
- Each mapper is independently testable against real fixture data
- The pattern is explicit and repeatable: the agent follows the same template for each new museum
- `MapperProtocol` ensures all mappers have the same interface while allowing different internal logic
- Structural tests (`test_structure.py`) verify that every registered museum has a mapper, ingest asset, and fixture data
